"""Command line: python -m pctimelogger [run | report | timeline | import-phone | info]

Without a command it starts the tray app, like PCTimeLogger.exe.
"""

import argparse
import logging
import sys
import threading
from datetime import date, timedelta
from logging.handlers import RotatingFileHandler

from . import db, phone_import, report
from .config import config_path, data_dir, load_config

log = logging.getLogger("pctimelogger")


def _setup_logging(verbose: bool) -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    handlers = [RotatingFileHandler(data_dir() / "pctimelogger.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")]
    if sys.stderr:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def _windows_only() -> bool:
    if sys.platform != "win32":
        print("Logimine töötab ainult Windowsis.", file=sys.stderr)
        return False
    return True


def cmd_app(args) -> int:
    if not _windows_only():
        return 1
    from .app import main as app_main

    return app_main()


def cmd_run(args) -> int:
    if not _windows_only():
        return 1
    from .service import run_logging

    stop = threading.Event()
    try:
        run_logging(load_config(), stop)
    except KeyboardInterrupt:
        stop.set()
    return 0


def _period(args) -> tuple[date, date]:
    today = date.today()
    if args.week:
        first = today - timedelta(days=today.weekday())
        return first, first + timedelta(days=6)
    if args.month:
        first = today.replace(day=1)
        nxt = (first + timedelta(days=32)).replace(day=1)
        return first, nxt - timedelta(days=1)
    first = date.fromisoformat(args.day or args.start) if (args.day or args.start) else today
    last = date.fromisoformat(args.end) if args.end else first
    return first, last


def cmd_report(args) -> int:
    conn = db.connect(load_config().db_path)
    first, last = _period(args)
    print(report.format_report(conn, first, last, top=args.top))
    return 0


def cmd_timeline(args) -> int:
    conn = db.connect(load_config().db_path)
    day = date.fromisoformat(args.day) if args.day else date.today()
    print(report.format_timeline(conn, day))
    return 0


def cmd_import_phone(args) -> int:
    cfg = load_config()
    folder = args.folder or cfg.phone_inbox
    if not folder:
        print("Telefoni kaust pole määratud. Lisa config.json faili phone_inbox või kasuta --folder.", file=sys.stderr)
        return 1
    count = phone_import.import_folder(db.connect(cfg.db_path), folder)
    print(f"Imporditi {count} telefoni kirjet.")
    return 0


def cmd_info(args) -> int:
    cfg = load_config()
    print(f"Seaded:     {config_path()}")
    print(f"Andmebaas:  {cfg.db_path}")
    print(f"Logifail:   {data_dir() / 'pctimelogger.log'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pctimelogger", description="PC ajalogija")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--installed", action="store_true", help=argparse.SUPPRESS)
    parser.set_defaults(func=cmd_app)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("run", help="logi aktiivset programmi ja faili taustal").set_defaults(func=cmd_run)

    rep = sub.add_parser("report", help="aeg programmide ja failide kaupa")
    rep.add_argument("--day", help="päev kujul AAAA-KK-PP (vaikimisi täna)")
    rep.add_argument("--start", help="vahemiku algus AAAA-KK-PP")
    rep.add_argument("--end", help="vahemiku lõpp AAAA-KK-PP")
    rep.add_argument("--week", action="store_true", help="see nädal")
    rep.add_argument("--month", action="store_true", help="see kuu")
    rep.add_argument("--top", type=int, default=20)
    rep.set_defaults(func=cmd_report)

    tl = sub.add_parser("timeline", help="päeva ajajoon")
    tl.add_argument("--day", help="päev kujul AAAA-KK-PP (vaikimisi täna)")
    tl.set_defaults(func=cmd_timeline)

    imp = sub.add_parser("import-phone", help="loe telefoni andmed Google Drive'i kaustast")
    imp.add_argument("--folder", help="kaust (vaikimisi config.json phone_inbox)")
    imp.set_defaults(func=cmd_import_phone)

    sub.add_parser("info", help="näita seadete ja andmebaasi asukohta").set_defaults(func=cmd_info)

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
