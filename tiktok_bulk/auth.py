"""Autentikasi: login interaktif dan verifikasi sesi tersimpan."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from playwright.sync_api import BrowserContext, Page

from .config import LOGIN, LOGIN_URL, UPLOAD_URL

logger = logging.getLogger(__name__)


def _has_sessionid(context: BrowserContext) -> bool:
    return any(c.get("name") == "sessionid" for c in context.cookies())


def is_logged_in(page: Page) -> bool:
    """Cek apakah halaman saat ini menampilkan UI studio (bukan halaman login)."""
    if "/login" in page.url:
        return False
    return _has_sessionid(page.context)


def login_interactive(page: Page, timeout_seconds: int = 300) -> bool:
    """Buka halaman login dan tunggu pengguna menyelesaikan login manual.

    Mendukung login lewat email/username, Google, atau QR code. Fungsi kembali
    ketika cookie ``sessionid`` muncul atau waktu habis.
    """
    logger.info("Membuka halaman login TikTok. Selesaikan login di jendela browser.")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")

    # Coba arahkan ke form email/username sebagai titik awal yang umum.
    try:
        switch = page.locator(f"xpath={LOGIN.switch_to_email}").first
        if switch.is_visible(timeout=5000):
            switch.click()
    except Exception:
        pass

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _has_sessionid(page.context):
            logger.info("Login berhasil, sesi disimpan.")
            return True
        time.sleep(2)

    logger.error("Waktu login habis tanpa cookie sessionid.")
    return False


def ensure_logged_in(page: Page, headless: bool) -> bool:
    """Pastikan sesi valid. Untuk headless, sesi lama harus sudah tersimpan."""
    page.goto(UPLOAD_URL, wait_until="domcontentloaded")
    if is_logged_in(page):
        return True
    if headless:
        logger.error(
            "Sesi tidak valid dan mode headless tidak bisa login manual. "
            "Jalankan 'login' tanpa --headless terlebih dahulu."
        )
        return False
    return login_interactive(page)


def save_session(context: BrowserContext, session_path: Path) -> None:
    session_path.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(session_path))
    logger.info("Sesi disimpan ke %s", session_path)
