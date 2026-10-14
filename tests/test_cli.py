"""Tes alur CLI upload dengan page tiruan (tanpa browser)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest

from tiktok_bulk import cli
from tiktok_bulk.manifest import VideoItem
from tiktok_bulk.uploader import upload_one

from .conftest import FakePage


@pytest.fixture()
def fake_page():
    return FakePage()


def test_dry_run_tidak_menekan_post(fake_page, tmp_path):
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x")
    item = VideoItem(path=video, caption="halo #fyp")

    outcome = upload_one(fake_page, item, dry_run=True)

    assert outcome.status == "skipped"
    assert "dry-run" in outcome.detail
    # Tidak boleh ada klik ke tombol post.
    assert not any("post_video_button" in str(a) for a in fake_page.actions)
    # File harus sudah dipilih.
    assert any(a[0] == "set_input_files" for a in fake_page.actions)


def test_caption_terisi(fake_page, tmp_path):
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x")
    item = VideoItem(path=video, caption="promo hari ini")

    upload_one(fake_page, item, dry_run=True)

    typed = "".join(a[1] for a in fake_page.actions if a[0] == "type")
    assert "promo" in typed and "hari" in typed


def test_file_tidak_ada_dilewati(fake_page, tmp_path):
    item = VideoItem(path=tmp_path / "hilang.mp4", caption="x")
    outcome = upload_one(fake_page, item, dry_run=True)
    assert outcome.status == "skipped"
    assert "tidak ditemukan" in outcome.detail


def test_run_upload_dry_run(tmp_path, monkeypatch):
    folder = tmp_path / "videos"
    folder.mkdir()
    (folder / "a.mp4").write_bytes(b"x")
    (folder / "b.mp4").write_bytes(b"x")

    page = FakePage()

    @contextmanager
    def fake_context(*args, **kwargs):
        yield object()

    monkeypatch.setattr(cli, "open_context", fake_context)
    monkeypatch.setattr(cli, "new_page", lambda ctx: page)
    monkeypatch.setattr(cli, "ensure_logged_in", lambda p, headless: True)

    report = tmp_path / "report.csv"
    code = cli.main(
        [
            "upload",
            str(folder),
            "--dry-run",
            "--caption",
            "halo",
            "--report",
            str(report),
        ]
    )

    assert code == 0
    assert report.exists()
    content = report.read_text(encoding="utf-8")
    assert "a.mp4" in content and "b.mp4" in content
    assert "skipped" in content


def test_run_upload_folder_kosong(tmp_path, monkeypatch):
    empty = tmp_path / "kosong"
    empty.mkdir()
    code = cli.main(["upload", str(empty), "--dry-run"])
    assert code == 2
