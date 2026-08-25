"""
Search the web for images of each name in role_model_summary.csv and save
a handful of them into mosaicPhotos/, for use as tiles in the photo mosaic.

Setup (one time):
    pip3 install ddgs requests

Usage:
    python3 fetch_role_model_photos.py

Re-running is safe: it skips names that already have enough saved images
(tracked in mosaicPhotos/.download_log.csv) and skips URLs it already tried.
"""

import csv
import re
import time
import unicodedata
from pathlib import Path

import requests
from ddgs import DDGS

CSV_PATH = Path("role_model_summary.csv")
IMG_FOLDER = Path("mosaicPhotos")
LOG_PATH = IMG_FOLDER / ".download_log.csv"
IMAGES_PER_NAME = 3
SEARCH_RESULTS_PER_NAME = 10  # pull extras in case some URLs fail to download
REQUEST_TIMEOUT = 15
PAUSE_BETWEEN_NAMES = 1.5  # seconds, be polite to the search backend

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def slugify(name: str) -> str:
    slug = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug).strip("_").lower()
    return slug or "unnamed"


def load_names() -> list[str]:
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row["role_model_summary"].strip() for row in reader if row["role_model_summary"].strip()]


def load_done_counts() -> dict[str, int]:
    """Read the log to see how many images we already have per name."""
    counts: dict[str, int] = {}
    if LOG_PATH.exists():
        with open(LOG_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("status") == "saved":
                    counts[row["name"]] = counts.get(row["name"], 0) + 1
    return counts


def append_log(rows: list[dict]) -> None:
    is_new = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "url", "status", "filename"])
        if is_new:
            writer.writeheader()
        writer.writerows(rows)


def guess_extension(url: str, content_type: str | None) -> str:
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if url.lower().split("?")[0].endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    if content_type:
        if "png" in content_type:
            return ".png"
        if "webp" in content_type:
            return ".webp"
        if "gif" in content_type:
            return ".gif"
    return ".jpg"


def download_image(url: str, dest_stub: Path) -> Path | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type and not any(
            url.lower().split("?")[0].endswith(e) for e in (".jpg", ".jpeg", ".png", ".webp", ".gif")
        ):
            return None
        dest = dest_stub.with_suffix(guess_extension(url, content_type))
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        if dest.stat().st_size < 2048:  # too small to be a real photo, likely an error page
            dest.unlink(missing_ok=True)
            return None
        return dest
    except Exception:
        return None


def main() -> None:
    IMG_FOLDER.mkdir(exist_ok=True)
    names = load_names()
    done_counts = load_done_counts()
    tried_urls: set[str] = set()
    if LOG_PATH.exists():
        with open(LOG_PATH, newline="", encoding="utf-8") as f:
            tried_urls = {row["url"] for row in csv.DictReader(f)}

    print(f"{len(names)} names in {CSV_PATH}")

    for i, name in enumerate(names, 1):
        have = done_counts.get(name, 0)
        if have >= IMAGES_PER_NAME:
            continue

        print(f"[{i}/{len(names)}] {name} (have {have}/{IMAGES_PER_NAME})", end=" ")

        try:
            with DDGS() as ddgs:
                results = list(ddgs.images(name, max_results=SEARCH_RESULTS_PER_NAME))
        except Exception as e:
            print(f"-- search failed: {e}")
            time.sleep(PAUSE_BETWEEN_NAMES)
            continue

        slug = slugify(name)
        log_rows = []
        saved_this_round = 0

        for result in results:
            if have + saved_this_round >= IMAGES_PER_NAME:
                break
            url = result.get("image")
            if not url or url in tried_urls:
                continue
            tried_urls.add(url)

            dest_stub = IMG_FOLDER / f"{slug}_{have + saved_this_round + 1}"
            saved_path = download_image(url, dest_stub)
            if saved_path:
                saved_this_round += 1
                log_rows.append({"name": name, "url": url, "status": "saved", "filename": saved_path.name})
            else:
                log_rows.append({"name": name, "url": url, "status": "failed", "filename": ""})

        if log_rows:
            append_log(log_rows)
        print(f"-- saved {saved_this_round}")

        time.sleep(PAUSE_BETWEEN_NAMES)

    print("Done.")


if __name__ == "__main__":
    main()
