"""Konfigurasi terpusat: URL, selector DOM, dan pengaturan waktu.

Selector mengikuti DOM TikTok Studio (creator center). TikTok sering mengubah
markup-nya, jadi semua selector dikumpulkan di sini agar mudah diperbarui tanpa
menyentuh logika alur. Jika sebuah langkah gagal karena halaman berubah, cukup
sesuaikan nilai di UPLOAD / LOGIN / SCHEDULE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Path & lokasi
# --------------------------------------------------------------------------- #
DEFAULT_HOME = Path.home() / ".tiktok_bulk"
DEFAULT_SESSION = DEFAULT_HOME / "session.json"
DEFAULT_LOG_DIR = DEFAULT_HOME / "logs"

UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload?from=creator_center&tab=video"
LOGIN_URL = "https://www.tiktok.com/login"

# --------------------------------------------------------------------------- #
# Jenis file
# --------------------------------------------------------------------------- #
VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".wmv",
    ".flv",
    ".webm",
    ".mkv",
    ".m4v",
    ".3gp",
    ".3g2",
    ".gif",
}
COVER_EXTENSIONS = {".png", ".jpg", ".jpeg"}

MAX_CAPTION_LENGTH = 2200


# --------------------------------------------------------------------------- #
# Selector DOM
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LoginSelectors:
    # Tombol untuk masuk ke form email/username.
    switch_to_email: str = "//div[contains(text(), 'Use phone / email / username')]"
    username_field: str = "//input[@name='username']"
    password_field: str = "//input[@type='password']"
    submit_button: str = "//button[@type='submit']"


@dataclass(frozen=True)
class ScheduleSelectors:
    switch: str = "//*[@id='tux-1']"
    date_picker: str = "//div[contains(@class, 'date-picker-input')]"
    calendar: str = "//div[contains(@class, 'calendar-wrapper')]"
    calendar_month: str = "//span[contains(@class, 'month-title')]"
    calendar_valid_days: str = (
        "//div[@class='jsx-4172176419 days-wrapper']"
        "//span[contains(@class, 'day') and contains(@class, 'valid')]"
    )
    calendar_arrows: str = "//span[contains(@class, 'arrow')]"
    time_picker: str = "//div[contains(@class, 'time-picker-input')]"
    time_picker_text: str = "//div[contains(@class, 'time-picker-input')]/*[1]"
    time_picker_container: str = "//div[@class='tiktok-timepicker-time-picker-container']"
    timepicker_hours: str = "//span[contains(@class, 'tiktok-timepicker-left')]"
    timepicker_minutes: str = "//span[contains(@class, 'tiktok-timepicker-right')]"


@dataclass(frozen=True)
class UploadSelectors:
    root: str = "#root"
    upload_input: str = "//input[@type='file' and not(@accept='image/png, image/jpeg, image/jpg')]"
    # Label resolusi muncul setelah TikTok selesai memproses video.
    process_confirmation: str = "//div[contains(@class, 'resolution-label-text')]"
    description: str = "//div[@contenteditable='true']"
    mention_box: str = "//div[contains(@class, 'mention-list-popover')]"
    mention_box_user_id: str = "//span[contains(@class, 'user-id')]"
    split_window: str = "//button[./div[text()='Not now']]"
    visibility_dropdown: str = (
        "//div[@data-e2e='video_visibility_container']//button[@role='combobox']"
    )
    post_button: str = "//button[@data-e2e='post_video_button']"
    post_now: str = "//button[.//div[text()='Post now']]"
    post_confirmation: str = (
        "//div[contains(text(), 'Your video has been uploaded') "
        "or contains(text(), 'Video published') "
        "or contains(text(), '视频已发布')]"
    )
    cookie_banner: str = "tiktok-cookie-banner"
    cookie_button: str = "div.button-wrapper >> button"


@dataclass(frozen=True)
class Timings:
    """Semua nilai dalam detik."""

    implicit: int = 30
    explicit: int = 60
    upload_process: int = 180
    hashtag_suggestion: int = 5
    between_videos: tuple[int, int] = (5, 15)
    after_click: float = 1.0


@dataclass(frozen=True)
class AppConfig:
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    viewport: dict = field(default_factory=lambda: {"width": 1280, "height": 800})
    locale: str = "en-US"


LOGIN = LoginSelectors()
SCHEDULE = ScheduleSelectors()
UPLOAD = UploadSelectors()
TIMINGS = Timings()
APP = AppConfig()
