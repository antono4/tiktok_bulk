"""CLI bulk upload TikTok Studio."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from .auth import ensure_logged_in, login_interactive
from .browser import new_page, open_context, session_exists
from .config import DEFAULT_LOG_DIR, DEFAULT_SESSION
from .manifest import ManifestError, build_queue
from .uploader import UploadOutcome, polite_delay, upload_one

logger = logging.getLogger("tiktok_bulk")


def _setup_logging(verbose: bool, log_dir: Path | None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        handlers.append(logging.FileHandler(log_dir / f"upload-{stamp}.log"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )


def _common_browser_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--session",
        type=Path,
        default=DEFAULT_SESSION,
        help=f"File sesi login (default: {DEFAULT_SESSION})",
    )
    parser.add_argument("--headless", action="store_true", help="Jalankan tanpa jendela")
    parser.add_argument("--channel", default=None, help="Channel browser (chrome/msedge)")
    parser.add_argument("--proxy", default=None, help="Proxy, mis. http://host:port")
    parser.add_argument("-v", "--verbose", action="store_true", help="Log detail")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tiktok-bulk",
        description="Upload video masal ke TikTok Studio secara otomatis.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="Login sekali dan simpan sesi")
    _common_browser_args(login)
    login.add_argument(
        "--timeout", type=int, default=300, help="Batas waktu login (detik)"
    )

    check = sub.add_parser("check", help="Verifikasi sesi login tersimpan")
    _common_browser_args(check)

    upload = sub.add_parser("upload", help="Upload semua video dalam folder")
    _common_browser_args(upload)
    upload.add_argument("folder", type=Path, help="Folder berisi video")
    upload.add_argument("--manifest", type=Path, default=None, help="CSV/JSON metadata")
    upload.add_argument("--recursive", action="store_true", help="Telusuri subfolder")
    upload.add_argument("--caption", default="", help="Caption default tanpa manifest")
    upload.add_argument(
        "--dry-run",
        action="store_true",
        help="Isi form tanpa menekan Post (uji coba)",
    )
    upload.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Jeda tetap antar video (detik); default acak 5-15 detik",
    )
    upload.add_argument("--limit", type=int, default=None, help="Batasi jumlah video")
    upload.add_argument(
        "--report", type=Path, default=None, help="Tulis ringkasan hasil ke CSV"
    )
    return parser


def _run_login(args: argparse.Namespace) -> int:
    with open_context(
        args.session,
        headless=args.headless,
        channel=args.channel,
        proxy=args.proxy,
    ) as context:
        page = new_page(context)
        ok = login_interactive(page, timeout_seconds=args.timeout)
    return 0 if ok else 1


def _run_check(args: argparse.Namespace) -> int:
    if not session_exists(args.session):
        logger.error("Tidak ada sesi tersimpan di %s.", args.session)
        return 1
    with open_context(
        args.session,
        headless=args.headless,
        channel=args.channel,
        proxy=args.proxy,
    ) as context:
        page = new_page(context)
        ok = ensure_logged_in(page, headless=args.headless)
    logger.info("Sesi %s.", "VALID" if ok else "TIDAK VALID")
    return 0 if ok else 1


def _write_report(path: Path, outcomes: list[UploadOutcome]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["file", "status", "detail"])
        for outcome in outcomes:
            writer.writerow([outcome.item.name, outcome.status, outcome.detail])
    logger.info("Laporan ditulis ke %s", path)


def _run_upload(args: argparse.Namespace) -> int:
    try:
        queue = build_queue(
            args.folder,
            manifest=args.manifest,
            recursive=args.recursive,
            default_caption=args.caption,
        )
    except (FileNotFoundError, NotADirectoryError, ManifestError) as exc:
        logger.error("%s", exc)
        return 2

    if args.limit:
        queue = queue[: args.limit]

    logger.info("Antrean: %d video%s", len(queue), " (dry-run)" if args.dry_run else "")

    outcomes: list[UploadOutcome] = []
    with open_context(
        args.session,
        headless=args.headless,
        channel=args.channel,
        proxy=args.proxy,
    ) as context:
        page = new_page(context)
        if not ensure_logged_in(page, headless=args.headless):
            logger.error("Login gagal; upload dibatalkan.")
            return 1

        for index, item in enumerate(queue, start=1):
            logger.info("[%d/%d] %s", index, len(queue), item.name)
            outcome = upload_one(page, item, dry_run=args.dry_run)
            outcomes.append(outcome)
            _log_outcome(outcome)
            if index < len(queue):
                _delay(args.delay)

    _print_summary(outcomes)
    if args.report:
        _write_report(args.report, outcomes)

    posted = sum(1 for o in outcomes if o.status == "posted")
    if args.dry_run:
        return 0
    return 0 if posted == len(outcomes) else 1


def _delay(fixed: float | None) -> None:
    if fixed is None:
        polite_delay()
    else:
        time.sleep(fixed)


def _log_outcome(outcome: UploadOutcome) -> None:
    if outcome.ok:
        logger.info("  -> berhasil")
    elif outcome.status == "skipped":
        logger.info("  -> dilewati: %s", outcome.detail)
    else:
        logger.warning("  -> gagal: %s", outcome.detail)


def _print_summary(outcomes: list[UploadOutcome]) -> None:
    posted = sum(1 for o in outcomes if o.status == "posted")
    failed = sum(1 for o in outcomes if o.status == "failed")
    skipped = sum(1 for o in outcomes if o.status == "skipped")
    logger.info("Selesai. berhasil=%d gagal=%d dilewati=%d", posted, failed, skipped)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    log_dir = None if getattr(args, "dry_run", False) else DEFAULT_LOG_DIR
    _setup_logging(args.verbose, log_dir)

    try:
        if args.command == "login":
            return _run_login(args)
        if args.command == "check":
            return _run_check(args)
        if args.command == "upload":
            return _run_upload(args)
    except PlaywrightError as exc:
        logger.error("Browser gagal dijalankan: %s", exc)
        if not args.headless:
            logger.error(
                "Di server tanpa layar, gunakan --headless setelah login sekali."
            )
        return 3

    parser.error("perintah tidak dikenal")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
