# RonsPortfolio

Source for my personal site — a plain HTML/CSS/JS page (no build step), meant to be served by GitHub Pages.

## Structure

- `index.html` — the whole site (About, Books, Projects, Contact)
- `assets/css/style.css` — styles (light/dark based on system preference)
- `assets/js/main.js` — mobile nav toggle, mosaic lightbox, headshot fallback, video autoplay-on-scroll
- `assets/img/` — web-optimized copies of images/video used on the page
- `Personal Tool Journey/` — source notebook, data, and original GIF for the tool-journey project
- `PhotoMosaic/` — source scripts, data, and original image for the mosaic project

## Preview locally

Just open `index.html` in a browser, or serve it:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Add a real headshot

Drop a photo in at `assets/img/headshot.jpg` (square-ish, at least 440x440px works well) — the
page already points at that path and will pick it up automatically. Until that file exists, it
falls back to an initials placeholder.

## Deploy to GitHub Pages

1. Create a repo named `<your-username>.github.io` on GitHub.
2. From this folder:
   ```bash
   git remote add origin git@github.com:<your-username>/<your-username>.github.io.git
   git branch -M main
   git push -u origin main
   ```
3. In the repo's Settings → Pages, set the source to the `main` branch, root folder (the
   `.nojekyll` file already in this repo skips Jekyll processing, so the site deploys as-is).
4. The site will be live at `https://<your-username>.github.io` within a few minutes.
