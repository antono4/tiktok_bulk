"""Pembacaan folder video dan manifest metadata (CSV / JSON).

Format manifest: satu baris per video, dengan kolom ``file`` sebagai kunci.
Kolom opsional: ``caption``/``description``, ``schedule``, ``visibility``,
``cover``. Nama file yang tidak ada di manifest tetap diunggah memakai nama file
sebagai caption.

Contoh CSV::

    file,caption,schedule,visibility
    promo1.mp4,"Promo hari ini #promo #diskon",2026-10-20 19:00,Public
    tips2.mp4,"3 tips cepat #tips",,
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import COVER_EXTENSIONS, MAX_CAPTION_LENGTH, VIDEO_EXTENSIONS

CAPTION_KEYS = ("caption", "description", "desc")
FILE_KEYS = ("file", "filename", "video", "video_path", "path")

VALID_VISIBILITY = {"public", "friends", "private"}


class ManifestError(ValueError):
    """Manifest tidak valid."""


@dataclass
class VideoItem:
    path: Path
    caption: str = ""
    schedule: datetime | None = None
    visibility: str = "Public"
    cover: Path | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.path.name


def discover_videos(folder: Path, recursive: bool = False) -> list[Path]:
    """Kembalikan daftar video di ``folder`` yang terurut secara natural."""
    if not folder.exists():
        raise FileNotFoundError(f"Folder tidak ditemukan: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Bukan sebuah folder: {folder}")

    pattern = "**/*" if recursive else "*"
    files = [
        p
        for p in folder.glob(pattern)
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return sorted(files, key=lambda p: str(p).lower())


def _pick(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        for candidate, value in row.items():
            if candidate.strip().lower() == key:
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                return value
    return None


def _parse_schedule(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ManifestError(
        f"Format jadwal tidak dikenali: {value!r}. "
        "Gunakan 'YYYY-MM-DD HH:MM' (waktu lokal)."
    )


def _normalize_visibility(value: Any) -> str:
    if value in (None, ""):
        return "Public"
    text = str(value).strip().capitalize()
    if text.lower() not in VALID_VISIBILITY:
        raise ManifestError(
            f"Visibility tidak valid: {value!r}. Pilih Public/Friends/Private."
        )
    return text


def load_manifest(path: Path, folder: Path) -> dict[str, VideoItem]:
    """Muat manifest dan kembalikan pemetaan nama-file -> VideoItem."""
    if not path.exists():
        raise FileNotFoundError(f"Manifest tidak ditemukan: {path}")

    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        rows = raw if isinstance(raw, list) else raw.get("videos", [])
    else:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))

    items: dict[str, VideoItem] = {}
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ManifestError(f"Baris {index} manifest bukan objek: {row!r}")

        file_value = _pick(row, FILE_KEYS)
        if not file_value:
            raise ManifestError(f"Baris {index} tidak punya kolom 'file'.")

        video_path = Path(str(file_value).strip())
        if not video_path.is_absolute():
            video_path = folder / video_path

        caption = _pick(row, CAPTION_KEYS) or ""
        caption = str(caption).strip()
        if len(caption) > MAX_CAPTION_LENGTH:
            raise ManifestError(
                f"Caption '{video_path.name}' melebihi {MAX_CAPTION_LENGTH} karakter."
            )

        cover_value = _pick(row, ("cover", "thumbnail", "cover_path"))
        cover: Path | None = None
        if cover_value:
            cover = Path(str(cover_value).strip())
            if not cover.is_absolute():
                cover = folder / cover
            if cover.suffix.lower() not in COVER_EXTENSIONS:
                raise ManifestError(f"Cover tidak didukung: {cover.name}")

        items[video_path.name] = VideoItem(
            path=video_path,
            caption=caption,
            schedule=_parse_schedule(_pick(row, ("schedule", "waktu", "jadwal"))),
            visibility=_normalize_visibility(
                _pick(row, ("visibility", "privacy", "privasi"))
            ),
            cover=cover,
        )
    return items


def build_queue(
    folder: Path,
    manifest: Path | None = None,
    recursive: bool = False,
    default_caption: str = "",
) -> list[VideoItem]:
    """Gabungkan file di folder dengan manifest menjadi antrean upload."""
    videos = discover_videos(folder, recursive=recursive)
    if not videos:
        raise FileNotFoundError(f"Tidak ada video yang didukung di {folder}")

    manifest_items = load_manifest(manifest, folder) if manifest else {}

    used = set()
    queue: list[VideoItem] = []
    for video in videos:
        item = manifest_items.get(video.name)
        if item is None:
            item = VideoItem(path=video, caption=default_caption)
        else:
            used.add(video.name)
        queue.append(item)

    for name in manifest_items.keys() - used:
        raise ManifestError(
            f"Manifest menyebut '{name}' tetapi file itu tidak ada di {folder}."
        )
    return queue
