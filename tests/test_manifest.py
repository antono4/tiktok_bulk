"""Tes parsing manifest, penemuan file, dan penjadwalan (tanpa browser)."""

from __future__ import annotations

from datetime import datetime

import pytest

from tiktok_bulk.manifest import (
    ManifestError,
    build_queue,
    discover_videos,
    load_manifest,
)


@pytest.fixture()
def folder(tmp_path):
    for name in ("b.mp4", "a.mp4", "c.mov", "notes.txt"):
        (tmp_path / name).write_bytes(b"x")
    return tmp_path


def test_discover_videos_urut_dan_filter(folder):
    found = [p.name for p in discover_videos(folder)]
    assert found == ["a.mp4", "b.mp4", "c.mov"]


def test_discover_videos_recursive(folder):
    sub = folder / "sub"
    sub.mkdir()
    (sub / "d.mp4").write_bytes(b"x")
    assert "d.mp4" in [p.name for p in discover_videos(folder, recursive=True)]
    assert "d.mp4" not in [p.name for p in discover_videos(folder)]


def test_discover_folder_tidak_ada(tmp_path):
    with pytest.raises(FileNotFoundError):
        discover_videos(tmp_path / "hilang")


def test_build_queue_default_caption(folder):
    queue = build_queue(folder, default_caption="halo")
    assert [i.name for i in queue] == ["a.mp4", "b.mp4", "c.mov"]
    assert all(i.caption == "halo" for i in queue)


def test_manifest_csv_lengkap(folder):
    manifest = folder / "m.csv"
    manifest.write_text(
        "file,caption,schedule,visibility\n"
        'a.mp4,"Halo #fyp",2026-11-01 09:00,Public\n'
        "b.mp4,Kedua,,Private\n",
        encoding="utf-8",
    )
    items = load_manifest(manifest, folder)
    assert items["a.mp4"].caption == "Halo #fyp"
    assert items["a.mp4"].schedule == datetime(2026, 11, 1, 9, 0)
    assert items["b.mp4"].visibility == "Private"
    assert items["b.mp4"].schedule is None


def test_manifest_json(folder):
    manifest = folder / "m.json"
    manifest.write_text(
        '[{"file": "a.mp4", "description": "json caption"}]', encoding="utf-8"
    )
    items = load_manifest(manifest, folder)
    assert items["a.mp4"].caption == "json caption"


def test_manifest_visibility_tidak_valid(folder):
    manifest = folder / "m.csv"
    manifest.write_text("file,visibility\na.mp4,Rahasia\n", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(manifest, folder)


def test_manifest_schedule_tidak_valid(folder):
    manifest = folder / "m.csv"
    manifest.write_text("file,schedule\na.mp4,besok pagi\n", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(manifest, folder)


def test_manifest_file_hilang(folder):
    manifest = folder / "m.csv"
    manifest.write_text("file,caption\nzzz.mp4,hilang\n", encoding="utf-8")
    with pytest.raises(ManifestError):
        build_queue(folder, manifest=manifest)


def test_manifest_caption_terlalu_panjang(folder):
    manifest = folder / "m.csv"
    manifest.write_text(f'file,caption\na.mp4,"{"x" * 2300}"\n', encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(manifest, folder)
