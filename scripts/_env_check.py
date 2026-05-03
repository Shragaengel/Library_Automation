import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://openlibrary.org", wait_until="domcontentloaded")
        await page.screenshot(path="screenshots/_env_check.png")
        title = await page.title()
        print(f"PAGE_TITLE: {title}")
        await browser.close()

asyncio.run(main())
