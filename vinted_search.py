"""
Vinted photo search via browser automation.

Vinted has a "Recherche à partir d'une image" button on vinted.fr identified by
data-testid="search-by-image-button". Clicking it opens a hidden file input;
we upload the photo and scrape the resulting listing cards.

Requires:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

VINTED_URL = "https://www.vinted.fr/"


def _parse_price(text: str) -> float | None:
    if not text:
        return None
    m = re.search(r"(\d+[.,]?\d*)", text.replace("\xa0", " "))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


CHROME_PROFILE = str(__import__("pathlib").Path.home() / ".playwright-chrome-profile")


def vinted_image_search(
    image_path: str, limit: int = 15, on_status=None, fetch_descriptions: int = 0
) -> list[dict]:
    results: list[dict] = []

    def _status(msg):
        if on_status:
            on_status(msg)

    _status("Launching browser...")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            CHROME_PROFILE,
            channel="chrome",
            headless=True,
            locale="fr-FR",
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = {runtime: {}};
        """)

        page = context.new_page()
        page.set_default_timeout(30000)
        _status("Opening Vinted...")
        page.goto(VINTED_URL, wait_until="domcontentloaded", timeout=30000)

        # Cookie banner — accept if present
        try:
            page.get_by_role("button", name=re.compile("accepter", re.I)).click(
                timeout=8000
            )
        except Exception:
            pass

        _status("Uploading image...")
        # Wait for the search-by-image button to be visible before clicking
        search_btn = page.locator('[data-testid="search-by-image-button"]').first
        search_btn.wait_for(state="visible", timeout=15000)
        search_btn.click()

        # Click reveals a hidden file input — set the file directly on it
        inputs = page.locator('input[type="file"]')
        inputs.first.wait_for(state="attached", timeout=10000)
        if inputs.count() > 0:
            inputs.first.set_input_files(image_path)
        else:
            context.close()
            raise RuntimeError("Could not find Vinted image-search input")
        _status("Waiting for results...")
        try:
            page.wait_for_selector(
                '[data-testid^="product-item-id-"]',
                timeout=30000,
            )
        except Exception as e:
            print(e)
            # Give it a bit more time on slow connections
            page.wait_for_timeout(8000)
        page.wait_for_timeout(3000)
        _status("Scrolling to load more listings...")
        for _ in range(3):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(800)

        _status("Extracting listings...")
        html = page.inner_html("body")
        soup = BeautifulSoup(html, "html.parser")

        card_els = soup.select('[data-testid^="product-item-id-"]')
        seen_urls: set[str] = set()
        for card in card_els:
            if len(results) >= limit:
                break
            try:
                a_tag = card.find("a")
                if not a_tag:
                    continue
                href = a_tag.get("href", "")
                if href.startswith("/"):
                    href = "https://www.vinted.fr" + href

                # Skip duplicates
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                title = a_tag.get("title", "")

                price_text = ""
                price_el = card.select_one('[data-testid$="--price-text"]')
                if not price_el:
                    price_el = card.find("p", string=re.compile("€"))
                if price_el:
                    price_text = price_el.get_text()

                thumb = ""
                img = card.find("img")
                if img:
                    thumb = img.get("src") or img.get("data-src") or ""
                    if not thumb or "placeholder" in thumb or thumb.startswith("data:"):
                        srcset = img.get("srcset", "")
                        if srcset:
                            thumb = srcset.split(",")[0].split()[0]

                brand = ""
                brand_el = card.select_one('[data-testid$="--description-title"]')
                if brand_el:
                    brand = brand_el.get_text()

                size = ""
                size_el = card.select_one('[data-testid$="--description-subtitle"]')
                if size_el:
                    size = size_el.get_text()

                results.append(
                    {
                        "url": href,
                        "title": title,
                        "price_eur": _parse_price(price_text),
                        "thumbnail": thumb,
                        "brand": brand,
                        "size": size,
                    }
                )
            except Exception:
                continue

        # --- Fetch full descriptions from individual listing pages ---
        if fetch_descriptions > 0 and results:
            n = min(fetch_descriptions, len(results))
            for idx in range(n):
                item = results[idx]
                url = item.get("url", "")
                if not url:
                    continue
                _status(f"Fetching description {idx + 1}/{n}...")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(1500)
                    desc_el = (
                        page.locator('[itemprop="description"]').first
                        or page.locator('[data-testid="item-description"]').first
                    )
                    desc_text = ""
                    if desc_el:
                        try:
                            desc_text = desc_el.inner_text(timeout=3000)
                        except Exception:
                            pass
                    if not desc_text:
                        # Fallback: try a broader selector
                        try:
                            fallback = page.locator('[class*="ItemDescription"]').first
                            desc_text = fallback.inner_text(timeout=3000)
                        except Exception:
                            pass
                    item["description"] = desc_text.strip()
                except Exception:
                    item["description"] = ""

        context.close()

    return results
