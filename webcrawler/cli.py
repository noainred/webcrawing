"""Command-line interface for the crawler."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional, Sequence

from . import storage
from .crawler import Crawler, CrawlConfig
from .fetcher import DEFAULT_USER_AGENT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="webcrawler",
        description="A small, polite HTML web crawler.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("urls", nargs="+", metavar="URL", help="one or more seed URLs")
    parser.add_argument("-d", "--max-depth", type=int, default=2,
                        help="how far to follow links from the seeds")
    parser.add_argument("-n", "--max-pages", type=int, default=100,
                        help="stop after fetching this many pages")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="minimum seconds between requests to the same host")
    parser.add_argument("--allow-external", action="store_true",
                        help="follow links to other domains (default: stay on seed host)")
    parser.add_argument("--no-subdomains", action="store_true",
                        help="treat subdomains as out of scope")
    parser.add_argument("--no-robots", action="store_true",
                        help="ignore robots.txt (use responsibly)")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--include", metavar="REGEX",
                        help="only crawl URLs matching this regex")
    parser.add_argument("--exclude", metavar="REGEX",
                        help="skip URLs matching this regex")
    parser.add_argument("-o", "--output", metavar="FILE",
                        help="write results to this file")
    parser.add_argument("-f", "--format", choices=["json", "jsonl", "csv"],
                        help="output format (default: infer from --output, else json)")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="-v for progress, -vv for debug")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="only print warnings and errors")
    return parser


def _configure_logging(verbose: int, quiet: bool) -> None:
    if quiet:
        level = logging.ERROR
    elif verbose >= 2:
        level = logging.DEBUG
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    _configure_logging(args.verbose, args.quiet)

    config = CrawlConfig(
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        delay=args.delay,
        same_domain=not args.allow_external,
        allow_subdomains=not args.no_subdomains,
        obey_robots=not args.no_robots,
        user_agent=args.user_agent,
        timeout=args.timeout,
        include=args.include,
        exclude=args.exclude,
    )

    crawler = Crawler(config)
    ok = errors = 0
    try:
        for page in crawler.crawl(args.urls):
            if page.error:
                errors += 1
                print(f"  x [{page.status_code or '-'}] {page.url}  ({page.error})", file=sys.stderr)
            else:
                ok += 1
                suffix = f"  - {page.title}" if page.title else ""
                print(f"  + [{page.status_code}] {page.url}{suffix}")
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
    finally:
        crawler.close()

    print(
        f"\nCrawled {len(crawler.pages)} page(s): {ok} ok, {errors} error(s).",
        file=sys.stderr,
    )

    if args.output:
        fmt = storage.save(crawler.pages, args.output, args.format)
        print(f"Saved {len(crawler.pages)} record(s) to {args.output} ({fmt}).", file=sys.stderr)

    return 0 if crawler.pages else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
