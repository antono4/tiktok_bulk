"""Engine upload satu video ke TikTok Studio via Playwright.

Alur per video mengikuti urutan UI TikTok Studio:
navigasi -> pilih file -> tunggu proses -> isi caption -> atur opsi
-> (jadwal) -> klik Post -> tunggu konfirmasi.

Semua aksi UI terisolasi di modul ini. Selector diambil dari ``config`` sehingga
perubahan DOM cukup diperbaiki di satu tempat.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from .config import SCHEDULE, TIMINGS, UPLOAD, UPLOAD_URL
from .manifest import VideoItem

logger = logging.getLogger(__name__)


class UploadError(RuntimeError):
    """Kegagalan yang bisa dipulihkan pada satu video."""


@dataclass
class UploadOutcome:
    item: VideoItem
    status: str  # "posted" | "failed" | "skipped"
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "posted"


# --------------------------------------------------------------------------- #
# Langkah-langkah UI
# --------------------------------------------------------------------------- #
def _dismiss_cookie_banner(page: Page) -> None:
    try:
        banner = page.locator(UPLOAD.cookie_banner).first
        if banner.is_visible(timeout=3000):
            button = banner.locator(UPLOAD.cookie_button.split(" >> ")[-1]).first
            if button.is_visible():
                button.click()
    except Exception:
        # Fallback: hapus node banner langsung dari DOM.
        page.evaluate(
            f"const b = document.querySelector('{UPLOAD.cookie_banner}');"
            "if (b) b.remove();"
        )


def _dismiss_split_window(page: Page) -> None:
    try:
        window = page.locator(f"xpath={UPLOAD.split_window}").first
        if window.is_visible(timeout=4000):
            window.click()
    except PlaywrightTimeoutError:
        pass
    except Exception:
        pass


def _go_to_upload(page: Page) -> None:
    if not page.url.startswith(UPLOAD_URL.split("?")[0]):
        page.goto(UPLOAD_URL, wait_until="domcontentloaded")
    page.wait_for_selector(UPLOAD.root, timeout=TIMINGS.explicit * 1000)


def _select_file(page: Page, item: VideoItem, retries: int = 3) -> None:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            upload_input = page.locator(f"xpath={UPLOAD.upload_input}").first
            upload_input.set_input_files(str(item.path))

            page.wait_for_selector(
                f"xpath={UPLOAD.process_confirmation}",
                state="attached",
                timeout=TIMINGS.upload_process * 1000,
            )
            return
        except Exception as exc:  # noqa: BLE001 - kita coba ulang
            last_error = exc
            logger.warning(
                "Percobaan %d/%d gagal memuat '%s': %s",
                attempt,
                retries,
                item.name,
                exc,
            )
            time.sleep(2)
    raise UploadError(f"Gagal memuat file '{item.name}': {last_error}")


def _set_caption(page: Page, caption: str) -> None:
    if not caption:
        return

    # Buang karakter di luar BMP agar TikTok tidak menolak input.
    caption = caption.encode("utf-8", "ignore").decode("utf-8")
    editor = page.locator(f"xpath={UPLOAD.description}").first
    editor.wait_for(state="visible", timeout=TIMINGS.implicit * 1000)
    editor.click()
    editor.press("Control+A")
    editor.press("Backspace")

    for word in caption.split(" "):
        if word.startswith("#"):
            editor.press_sequentially(word, delay=50)
            time.sleep(0.5)
            try:
                suggestion = page.locator(f"xpath={UPLOAD.mention_box}").first
                suggestion.wait_for(
                    state="visible", timeout=TIMINGS.hashtag_suggestion * 1000
                )
                editor.press("Enter")
            except PlaywrightTimeoutError:
                editor.press_sequentially(" ")
        elif word.startswith("@"):
            editor.press_sequentially(word, delay=50)
            time.sleep(1)
            _pick_mention(page, editor, word[1:])
        else:
            editor.press_sequentially(word + " ", delay=30)


def _pick_mention(page: Page, editor, username: str) -> None:
    try:
        options = page.locator(f"xpath={UPLOAD.mention_box_user_id}").all()
        target = username.lower()
        for index, option in enumerate(options):
            if not option.is_visible():
                continue
            text = option.inner_text().split(" ")[0].lower()
            if text == target:
                for _ in range(index):
                    editor.press("ArrowDown")
                editor.press("Enter")
                return
        editor.press_sequentially(" ")
    except Exception:
        editor.press_sequentially(" ")


def _set_visibility(page: Page, visibility: str) -> None:
    if visibility.lower() == "public":
        return
    try:
        dropdown = page.locator(f"xpath={UPLOAD.visibility_dropdown}").first
        dropdown.click()
        time.sleep(1.5)
        option = page.locator(
            f"//div[@role='option' and contains(., '{visibility}')]"
        ).first
        option.scroll_into_view_if_needed()
        option.click()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gagal mengatur visibility '%s': %s", visibility, exc)


def _set_schedule(page: Page, schedule: datetime) -> None:
    """Atur jadwal publikasi. TikTok hanya menerima kelipatan 5 menit."""
    if schedule.minute % 5:
        schedule = schedule.replace(
            minute=(schedule.minute // 5) * 5, second=0, microsecond=0
        )
    if schedule < datetime.now() + timedelta(minutes=20):
        raise UploadError(
            f"Jadwal {schedule} harus minimal 20 menit dari sekarang."
        )

    try:
        page.locator(f"xpath={SCHEDULE.switch}").first.click()
        _pick_date(page, schedule.month, schedule.day)
        _pick_time(page, schedule.hour, schedule.minute)
    except UploadError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise UploadError(f"Gagal mengatur jadwal: {exc}") from exc


def _pick_date(page: Page, month: int, day: int) -> None:
    page.locator(f"xpath={SCHEDULE.date_picker}").first.click()
    calendar = page.locator(f"xpath={SCHEDULE.calendar}").first
    calendar.wait_for(state="visible")

    month_title = page.locator(f"xpath={SCHEDULE.calendar_month}").first.inner_text()
    current = datetime.strptime(month_title.strip(), "%B").month
    if current != month:
        arrows = page.locator(f"xpath={SCHEDULE.calendar_arrows}")
        (arrows.last if current < month else arrows.first).click()

    for day_cell in page.locator(f"xpath={SCHEDULE.calendar_valid_days}").all():
        if day_cell.inner_text().strip() == str(day):
            day_cell.click()
            return
    raise UploadError(f"Tanggal {day} tidak tersedia di kalender.")


def _pick_time(page: Page, hour: int, minute: int) -> None:
    page.locator(f"xpath={SCHEDULE.time_picker}").first.click()
    container = page.locator(f"xpath={SCHEDULE.time_picker_container}").first
    container.wait_for(state="visible")

    hours = page.locator(f"xpath={SCHEDULE.timepicker_hours}")
    minutes = page.locator(f"xpath={SCHEDULE.timepicker_minutes}")

    hour_cell = hours.nth(hour)
    hour_cell.scroll_into_view_if_needed()
    time.sleep(0.3)
    hour_cell.click()

    minute_cell = minutes.nth(int(minute / 5))
    minute_cell.scroll_into_view_if_needed()
    time.sleep(0.3)
    minute_cell.click()

    page.locator(f"xpath={SCHEDULE.time_picker}").first.click()


def _click_post(page: Page) -> None:
    post_button = page.locator(f"xpath={UPLOAD.post_button}").first
    deadline = time.time() + TIMINGS.upload_process
    while time.time() < deadline:
        if post_button.get_attribute("data-disabled") == "false":
            break
        time.sleep(2)

    post_button.scroll_into_view_if_needed()
    post_button.click()

    # Dialog konfirmasi "Post now" kadang muncul saat penjadwalan.
    try:
        post_now = page.locator(f"xpath={UPLOAD.post_now}").first
        if post_now.is_visible(timeout=5000):
            post_now.click()
    except Exception:
        pass

    page.wait_for_selector(
        f"xpath={UPLOAD.post_confirmation}",
        timeout=TIMINGS.explicit * 1000,
    )


# --------------------------------------------------------------------------- #
# Orkestrasi
# --------------------------------------------------------------------------- #
def upload_one(page: Page, item: VideoItem, dry_run: bool = False) -> UploadOutcome:
    """Unggah satu video. ``dry_run`` hanya mengisi form tanpa klik Post."""
    if not item.path.exists():
        return UploadOutcome(item, "skipped", "file tidak ditemukan")

    try:
        _go_to_upload(page)
        _dismiss_cookie_banner(page)
        _select_file(page, item)
        _dismiss_split_window(page)
        _set_caption(page, item.caption)
        _set_visibility(page, item.visibility)
        if item.schedule:
            _set_schedule(page, item.schedule)
    except UploadError as exc:
        return UploadOutcome(item, "failed", str(exc))
    except PlaywrightError as exc:
        return UploadOutcome(item, "failed", f"error browser: {exc}")

    if dry_run:
        return UploadOutcome(item, "skipped", "dry-run: form siap, tidak di-post")

    try:
        _click_post(page)
    except PlaywrightTimeoutError:
        return UploadOutcome(item, "failed", "tidak ada konfirmasi publikasi")
    except PlaywrightError as exc:
        return UploadOutcome(item, "failed", f"error saat post: {exc}")

    return UploadOutcome(item, "posted")


def polite_delay() -> float:
    low, high = TIMINGS.between_videos
    delay = random.uniform(low, high)
    logger.debug("Jeda antar video %.1f detik", delay)
    time.sleep(delay)
    return delay
