# Terminal profile art — setup (≈10 minutes)

## 1. Your profile repo
Your profile repo `Chetanya-Kaushal/Chetanya-Kaushal` already exists. Copy these files into it.
This README replaces the current one (dot-matrix portrait + typing banner), so keep a copy of the old README if you want it.

## 2. Personalise (already done)
`scripts/config.py` holds your username, handle and card rows. Edit and re-run `make_info_card.py` to change them.

## 3. Make your art (on your computer)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r scripts/requirements.txt -r scripts/requirements-portrait.txt

python scripts/prep_photo.py source-photo.jpg   # a well-lit head-and-shoulders photo works best
python scripts/make_ascii_svg.py                # -> ascii-portrait.svg
python scripts/make_info_card.py                # -> info-card.svg
python scripts/fetch_contributions.py           # -> data/contributions.json
python scripts/render_heatmap_svg.py            # -> contrib-heatmap.svg
```
Open the `.svg` files in a browser to watch the animations.
Add `STATIC=1` before any command to get a frozen frame.

## 4. Push
```bash
git add . && git commit -m "animated terminal profile" && git push
```
The push triggers the workflow once; after that it refreshes the heatmap daily at ~11:47 IST.
You can also run it by hand: **Actions → Update profile art → Run workflow**.

If the workflow can't push, go to **Settings → Actions → General → Workflow permissions** and pick **Read and write**.

## Tuning
- Portrait too dark or noisy → raise `WHITE_CUTOFF` or change `COLS` in `make_ascii_svg.py`.
- Typing too slow/fast → `ROW_STAGGER` / `ROW_DUR`.
- The SVGs included are already generated from your GitHub photo and your real contributions, so step 3 is optional.
- Background removal uses GrabCut when rembg isn't installed; `pip install rembg` gives cleaner edges.
- `INVERT=0 python scripts/make_ascii_svg.py` gives the blog's original look (dark hair/beard drawn densest).
