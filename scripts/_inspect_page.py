"""
Selector verification helper.

Usage:
    python scripts/_inspect_page.py <url> <selector> [<selector>...]

For each selector, navigates once to <url> and reports:
  - Count of matching elements
  - Whether the first match is visible
  - A 200-char outerHTML snippet (when count == 1)

Output format per selector:
  [OK|WARN|FAIL]  count=N  visible=<bool>  selector=<selector>
"""

import asyncio
import io
import sys

# Force UTF-8 output so the script works on Windows terminals with non-UTF codepages.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright


_OUTER_HTML_LIMIT = 200
_TIMEOUT_MS = 30_000


def _badge(count: int, visible: bool) -> str:
    if count == 0:
        return "[FAIL]"
    if count == 1 and visible:
        return "[OK]  "
    return "[WARN]"


async def inspect(url: str, selectors: list[str]) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(_TIMEOUT_MS)

        print(f"\nURL: {url}\n{'-' * 60}")
        await page.goto(url, wait_until="domcontentloaded")

        for selector in selectors:
            try:
                loc = page.locator(selector)
                count = await loc.count()

                if count > 0:
                    try:
                        visible = await loc.first.is_visible()
                    except Exception:
                        visible = False
                else:
                    visible = False

                badge = _badge(count, visible)
                line = f"{badge}  count={count}  visible={str(visible):<5}  selector={selector}"
                print(line)

                # Extra context when there is exactly one match
                if count == 1:
                    try:
                        html = await loc.first.evaluate("el => el.outerHTML")
                        snippet = html.replace("\n", " ").strip()[:_OUTER_HTML_LIMIT]
                        print(f"    HTML: {snippet}")
                    except Exception:
                        pass

            except Exception as exc:
                print(f"[FAIL]  count=?  visible=False  selector={selector}  ERROR={exc}")

        await browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/_inspect_page.py <url> <selector> [<selector>...]")
        sys.exit(1)

    target_url = sys.argv[1]
    target_selectors = sys.argv[2:]
    asyncio.run(inspect(target_url, target_selectors))
