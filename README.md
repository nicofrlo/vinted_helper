# Vinted Seller Helper

Upload a clothing photo → get Vinted price comparables + candidate model photos for your listing.

## What it does

1. **Local vision model** (Qwen2.5-VL via Ollama) describes the garment in French and produces search keywords.
2. **Vinted photo search** (browser-automated through Playwright, using Vinted's real "Recherche à partir d'une image" button) returns visually similar listings with their prices.
3. **Google Images scrape** with the keywords + "porté" returns candidate model photos you can use to illustrate your listing.

All inside a small Streamlit web app.

## One-time setup (M1 Mac)

```bash
# 1. Ollama model (pick one)
ollama pull qwen2.5vl:7b      # recommended on M1 (~5 GB)
# or:
ollama pull qwen2.5vl:3b      # lighter

# 2. Python deps (use a venv)
cd vinted-helper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Playwright browser
playwright install chromium
```

Make sure Ollama is running (the menu-bar app, or `ollama serve`).

## Run

```bash
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

## Notes & gotchas

- **First Vinted run may show a cookie banner**; the script clicks "Accepter" automatically. If Vinted's markup changes, the click selectors in `vinted_search.py` are the things to update — they're all in one place.
- **Headless mode**: if Vinted blocks the headless browser, edit `vinted_search.py` and set `headless=False` to debug visually.
- **Rate limit yourself.** This is for personal use on your own clothes. Don't hammer Vinted — once every few minutes is fine, hundreds of requests an hour will get your IP throttled.
- **Google Images scraping is fragile** by design (you chose this over SerpAPI). If it stops returning results, Google probably changed their HTML; the regexes in `google_images.py` are the place to fix.
- **Model choice**: if `qwen2.5vl:7b` feels slow, switch to `qwen2.5vl:3b` in `describe.py` (one line at the top).
- **Legal**: scraping Vinted is against their ToS. At personal-use volumes the practical risk is just an IP throttle, but you should know.

## Files

```
vinted-helper/
├── app.py              # Streamlit UI
├── describe.py         # Ollama / Qwen2.5-VL caller
├── vinted_search.py    # Playwright Vinted automation
├── google_images.py    # Google Images scraper
├── requirements.txt
└── README.md
```

## If something breaks

- **Ollama error** → is `ollama serve` running? Did you `ollama pull qwen2.5vl:7b`?
- **Vinted returns 0 results** → run with `headless=False` in `vinted_search.py` and watch what happens. Vinted occasionally renames `data-testid` attributes.
- **Google returns 0 images** → Google changed their markup. Update the regex in `google_images.py`, or sign up for SerpAPI for a robust path.
