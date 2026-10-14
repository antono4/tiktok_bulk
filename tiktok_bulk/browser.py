"""Pembuatan browser Playwright dan persistensi sesi login.

Sesi disimpan sebagai ``storage_state`` (cookie + localStorage). Login hanya
perlu dilakukan sekali; sesi berikutnya memuat file yang sama sehingga tidak
perlu memasukkan ulang kredensial.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from .config import APP, TIMINGS

# Sembunyikan flag otomasi agar halaman tidak langsung menandai sebagai bot.
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = window.chrome || { runtime: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
"""


def session_exists(session_path: Path) -> bool:
    return session_path.exists() and session_path.stat().st_size > 0


@contextmanager
def open_context(
    session_path: Path,
    headless: bool = False,
    channel: str | None = None,
    proxy: str | None = None,
    slow_mo: int = 0,
) -> Iterator[BrowserContext]:
    """Buka BrowserContext, memuat sesi tersimpan bila ada.

    Mengembalikan context sehingga pemanggil dapat menyimpan ``storage_state``
    kembali ke ``session_path`` setelah selesai.
    """
    with sync_playwright() as playwright:
        launch_args: dict = {
            "headless": headless,
            "args": ["--disable-blink-features=AutomationControlled"],
            "slow_mo": slow_mo,
        }
        if channel:
            launch_args["channel"] = channel
        if proxy:
            launch_args["proxy"] = {"server": proxy}

        browser: Browser = playwright.chromium.launch(**launch_args)

        context_args: dict = {
            "viewport": APP.viewport,
            "user_agent": APP.user_agent,
            "locale": APP.locale,
            "timezone_id": "Asia/Jakarta",
        }
        if session_exists(session_path):
            context_args["storage_state"] = str(session_path)

        context = browser.new_context(**context_args)
        context.add_init_script(_STEALTH_SCRIPT)
        context.set_default_timeout(TIMINGS.implicit * 1000)
        context.set_default_navigation_timeout(TIMINGS.explicit * 1000)

        try:
            yield context
        finally:
            try:
                session_path.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(session_path))
            finally:
                context.close()
                browser.close()


def new_page(context: BrowserContext) -> Page:
    return context.new_page()
