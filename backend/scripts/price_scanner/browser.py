"""Playwright with the saved profile in backend/.browser_profile.

`login` opens a visible browser once, so a person can accept cookies, solve a captcha, log
in and pick a PLZ; the profile keeps all of it. `BrowserSession` reuses the profile for
scans: one tab, pages one after another at a person's pace (a pause between pages,
scrolling so lazy-loaded prices appear), a few dozen pages per store and week.

Playwright is imported inside the functions: it is only in requirements-scraper.txt, and
the rest of the scanner, and its tests, must work without it.
"""

import asyncio
import random
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any

from scripts.price_scanner.capture import Capture, PageImage, clean_text
from scripts.price_scanner.config import PROFILE_DIR, ScannerError

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page, Playwright

# Austrian shops show prices for the chosen PLZ/store; German locale, Vienna time.
CONTEXT_OPTIONS: dict[str, Any] = {"locale": "de-AT", "timezone_id": "Europe/Vienna"}
VIEWPORT = {"width": 1366, "height": 900}
NAVIGATION_TIMEOUT_MS = 45_000
SETTLE_TIMEOUT_MS = 10_000
PAUSE_BETWEEN_PAGES_S = (3.0, 7.0)
SCROLL_STEPS = (3, 6)
SCROLL_PAUSE_S = (0.4, 1.2)
# Less text than this (a cookie wall, a page drawn on a canvas): the screenshot goes to the
# model as well.
MIN_TEXT_CHARS = 200
SCREENSHOT_QUALITY = 80

INSTALL_HINT = (
    "Playwright is not installed: pip install -r requirements-scraper.txt "
    "&& python -m playwright install chromium"
)


async def _start_playwright() -> "Playwright":
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        raise ScannerError(INSTALL_HINT) from e
    return await async_playwright().start()


async def _pause(bounds: tuple[float, float]) -> None:
    await asyncio.sleep(random.uniform(*bounds))


async def login(urls: Sequence[str], profile_dir: Path = PROFILE_DIR) -> None:
    """Open `urls` in a visible browser and wait until the person closes every tab."""
    pw = await _start_playwright()
    from playwright.async_api import Error as PlaywrightError

    profile_dir.mkdir(exist_ok=True)
    context = await pw.chromium.launch_persistent_context(
        str(profile_dir), headless=False, no_viewport=True, **CONTEXT_OPTIONS
    )
    try:
        for index, url in enumerate(urls):
            page = context.pages[0] if index == 0 and context.pages else await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
            except PlaywrightError as e:
                print(f"Could not open {url}: {e.message.splitlines()[0]}")
        print(
            "In the browser: accept the cookie banners, solve any captcha, log in and pick "
            "your PLZ / store in every tab.\nClose the browser window when you're done; "
            "the profile is saved to " + str(profile_dir)
        )
        while context.pages:  # empty once every tab (or the browser) is closed
            await asyncio.sleep(1)
    finally:
        try:
            await context.close()  # flushes cookies and storage to the profile
        except PlaywrightError:
            pass  # the person quit the browser itself
        await pw.stop()


class BrowserSession:
    """A headless (or `headed`) browser on the saved profile, reading one page at a time.

    Screenshots go to `screenshot_dir` for review; pages with too little text also send
    their screenshot to the model.
    """

    def __init__(
        self,
        screenshot_dir: Path,
        headed: bool = False,
        profile_dir: Path = PROFILE_DIR,
    ) -> None:
        self.screenshot_dir = screenshot_dir
        self.headed = headed
        self.profile_dir = profile_dir
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._pages_read = 0

    async def __aenter__(self) -> "BrowserSession":
        if not self.profile_dir.is_dir():
            raise ScannerError(f"No browser profile at {self.profile_dir}: run with --login first")
        self._playwright = await _start_playwright()
        try:
            self._context = await self._playwright.chromium.launch_persistent_context(
                str(self.profile_dir),
                headless=not self.headed,
                viewport=VIEWPORT,
                **CONTEXT_OPTIONS,
            )
        except Exception:
            await self._playwright.stop()
            raise
        pages = self._context.pages
        self._page = pages[0] if pages else await self._context.new_page()
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._context is not None:
            await self._context.close()
        if self._playwright is not None:
            await self._playwright.stop()

    async def capture(self, url: str) -> Capture:
        """Load `url`, scroll through it and return its text (and a screenshot)."""
        from playwright.async_api import Error as PlaywrightError

        if self._page is None:
            raise RuntimeError("use BrowserSession as `async with`")
        page = self._page
        if self._pages_read:
            await _pause(PAUSE_BETWEEN_PAGES_S)
        self._pages_read += 1
        try:
            response = await page.goto(
                url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS
            )
            if response is not None and response.status >= 400:
                raise ScannerError(f"HTTP {response.status}")
            await _settle(page)
            await _scroll_through(page)
            text = clean_text(await _main_text(page))
            await page.evaluate("window.scrollTo(0, 0)")
            shot = await page.screenshot(type="jpeg", quality=SCREENSHOT_QUALITY)
        except PlaywrightError as e:
            raise ScannerError(e.message.splitlines()[0]) from e
        path = self.screenshot_dir / f"{self._pages_read:03d}.jpg"
        path.write_bytes(shot)
        images = (PageImage(shot, "image/jpeg"),) if len(text) < MIN_TEXT_CHARS else ()
        return Capture(source=url, text=text or None, images=images, screenshot=str(path))


async def _settle(page: "Page") -> None:
    """Wait until the page stops loading, up to a limit: shop pages keep tracking requests
    open, so "network idle" may never come."""
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    try:
        await page.wait_for_load_state("networkidle", timeout=SETTLE_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        pass


async def _scroll_through(page: "Page") -> None:
    for _ in range(random.randint(*SCROLL_STEPS)):
        await page.mouse.wheel(0, random.randint(400, 800))
        await _pause(SCROLL_PAUSE_S)


async def _main_text(page: "Page") -> str:
    """The text of the page's <main> (without header, menus and footer), else of <body>."""
    main = page.locator("main")
    target = main.first if await main.count() else page.locator("body")
    return await target.inner_text(timeout=SETTLE_TIMEOUT_MS)


def run_folder(runs_dir: Path, now: datetime) -> Path:
    """Folder for one run's screenshots: .scanner/20261110-083000."""
    return runs_dir / now.strftime("%Y%m%d-%H%M%S")
