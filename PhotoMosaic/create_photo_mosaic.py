"""
Build a photo mosaic entirely in Python (no RSimMosaic / R needed).

Replaces every cell of a downsampled copy of the target image with a
close-color-matching tile from a folder of tile images. Every time a tile
gets used, its effective color distance grows for future cells, so it keeps
getting outranked by fresher tiles until usage evens back out -- the result
draws from a much wider slice of the tile library instead of leaning on
whichever handful of tiles are the closest match overall.

Setup (one time):
    pip3 install Pillow numpy

Usage:
    python3 create_photo_mosaic.py
    python3 create_photo_mosaic.py --target loveTechnology.jpeg --grid-height 120 --tile-size 60

Run with --help to see all options.
"""

import argparse
import random
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None  # mosaics can get large; don't trip Pillow's decompression-bomb guard


def load_tile(path: Path, size: int) -> Image.Image | None:
    try:
        img = Image.open(path)
        img.load()
    except Exception:
        return None

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")

    w, h = img.size
    if w == 0 or h == 0:
        return None
    m = min(w, h)
    left, top = (w - m) // 2, (h - m) // 2
    img = img.crop((left, top, left + m, top + m)).resize((size, size), Image.LANCZOS)
    return img


def build_tile_library(tiles_dir: Path, tile_size: int):
    images, colors = [], []
    for path in sorted(tiles_dir.iterdir()):
        if path.name.startswith("."):
            continue
        tile = load_tile(path, tile_size)
        if tile is None:
            continue
        images.append(tile)
        colors.append(np.array(tile, dtype=np.float32).reshape(-1, 3).mean(axis=0))
    if not images:
        raise SystemExit(f"No usable tile images found in {tiles_dir}")
    return images, np.array(colors, dtype=np.float32)


def build_mosaic(
    target_path: Path,
    tiles_dir: Path,
    output_path: Path,
    grid_height: int,
    tile_size: int,
    repeat_penalty: float,
    max_uses_multiplier: float,
    top_k: int,
    blend: float,
    seed: int,
) -> None:
    random.seed(seed)

    print(f"Loading tiles from {tiles_dir} ...")
    tile_images, tile_colors = build_tile_library(tiles_dir, tile_size)
    print(f"  {len(tile_images)} usable tiles")

    target = Image.open(target_path).convert("RGB")
    grid_width = max(1, round(grid_height * target.width / target.height))
    small = target.resize((grid_width, grid_height), Image.LANCZOS)
    target_pixels = np.array(small, dtype=np.float32)  # (grid_height, grid_width, 3)
    total_cells = grid_width * grid_height
    print(f"Grid: {grid_width} x {grid_height} = {total_cells} cells")

    # Safety net only: an absolute ceiling on reuse so nothing can blanket the whole
    # mosaic. The real variety control is the progressive repeat_penalty below, which
    # makes an already-used tile look progressively farther away in color the more
    # it's been picked, so fresher tiles keep winning until usage evens back out.
    avg_uses = total_cells / len(tile_images)
    max_uses = max(1, int(np.ceil(avg_uses * max_uses_multiplier)))
    print(f"Average uses per tile: {avg_uses:.1f}, hard ceiling {max_uses}")

    output = Image.new("RGB", (grid_width * tile_size, grid_height * tile_size))
    usage = np.zeros(len(tile_images), dtype=np.int32)

    for row in range(grid_height):
        row_colors = target_pixels[row]  # (grid_width, 3)
        diffs = row_colors[:, None, :] - tile_colors[None, :, :]  # (grid_width, N, 3)
        dists = np.einsum("ijk,ijk->ij", diffs, diffs)  # squared distance, (grid_width, N)

        for col in range(grid_width):
            # Penalize each tile's distance in proportion to how often it's already
            # been used, so a tile that's a great match doesn't dominate -- it keeps
            # getting outranked by less-used tiles until usage evens out. Then
            # randomize among the closest (adjusted) matches rather than always taking
            # the single nearest, so smooth-color regions don't fill with a straight
            # repeating run of the same tile.
            d = dists[col] * (1.0 + repeat_penalty * usage)
            d[usage >= max_uses] = np.inf
            candidates = np.argsort(d)[:top_k]
            candidates = candidates[np.isfinite(d[candidates])]
            if candidates.size == 0:
                candidates = np.argsort(d)[:1]
            weights = 1.0 / (d[candidates] + 1.0)
            best = int(random.choices(candidates.tolist(), weights=weights.tolist(), k=1)[0])
            usage[best] += 1

            tile = tile_images[best]
            if blend > 0:
                target_color = tuple(int(c) for c in row_colors[col])
                solid = Image.new("RGB", tile.size, target_color)
                tile = Image.blend(tile, solid, blend)

            output.paste(tile, (col * tile_size, row * tile_size))

        if (row + 1) % 10 == 0 or row + 1 == grid_height:
            print(f"  row {row + 1}/{grid_height}")

    output.save(output_path, quality=92)
    print(f"Saved {output_path} ({output.size[0]}x{output.size[1]})")
    print(f"Most-used tile appears {usage.max()} times; least-used {usage.min()} times")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", default="loveTechnology.jpeg", help="Image the mosaic should depict")
    p.add_argument("--tiles-dir", default="mosaicPhotos", help="Folder of tile images")
    p.add_argument("--output", default=None, help="Output file (default: <target>_mosaic.jpeg)")
    p.add_argument("--grid-height", type=int, default=120, help="Number of tile rows (columns follow the target's aspect ratio)")
    p.add_argument("--tile-size", type=int, default=60, help="Pixel size of each square tile in the output")
    p.add_argument("--repeat-penalty", type=float, default=0.6, help="How much an already-used tile's effective color distance grows per prior use (0 = pure best-color-match, no variety control; higher = more even spread across the whole library)")
    p.add_argument("--max-uses-multiplier", type=float, default=3.0, help="Absolute safety ceiling on any tile's reuse, as a multiple of the average (cells / tiles). Rarely hit if repeat-penalty is doing its job")
    p.add_argument("--top-k", type=int, default=6, help="Randomize among this many closest (penalty-adjusted) color matches instead of always taking the single nearest, to avoid repeating runs")
    p.add_argument("--blend", type=float, default=0.0, help="0-1: how much to tint each tile toward the target color (0 = raw photo tiles)")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main():
    args = parse_args()
    target_path = Path(args.target)
    output_path = Path(args.output) if args.output else target_path.with_name(f"{target_path.stem}_mosaic.jpeg")
    build_mosaic(
        target_path=target_path,
        tiles_dir=Path(args.tiles_dir),
        output_path=output_path,
        grid_height=args.grid_height,
        tile_size=args.tile_size,
        repeat_penalty=args.repeat_penalty,
        max_uses_multiplier=args.max_uses_multiplier,
        top_k=args.top_k,
        blend=args.blend,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
