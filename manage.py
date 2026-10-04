#!/usr/bin/env python3
"""Central project-management entrypoint for Demonthrone."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from backend.app import DEFAULT_HOST, DEFAULT_PORT, run_server
from tools.pages import build_pages, preview_pages

PROJECT_ROOT = Path(__file__).resolve().parent


def build_frontend() -> None:
    """Compile the TypeScript frontend into browser-ready modules."""

    subprocess.run(
        ("npm", "run", "build"),
        cwd=PROJECT_ROOT,
        check=True,
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the project command-line interface."""

    parser = argparse.ArgumentParser(description="Build and run Demonthrone.")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("build", help="compile the TypeScript frontend")
    commands.add_parser("pages", help="build the landing page and playable demo for GitHub Pages")
    commands.add_parser("preview-pages", help="capture desktop, mobile, and game previews (requires Chromium)")

    server_parser = commands.add_parser(
        "runserver",
        help="build the frontend and start the HTTP server",
    )
    server_parser.add_argument("--host", default=DEFAULT_HOST)
    server_parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    server_parser.add_argument(
        "--no-build",
        action="store_true",
        help="start the server without rebuilding the frontend",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Run the requested project-management command."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        arguments.append("runserver")
    args = create_parser().parse_args(arguments)
    if args.command == "build":
        build_frontend()
        return
    if args.command == "pages":
        build_frontend()
        build_pages(PROJECT_ROOT)
        return
    if args.command == "preview-pages":
        preview_pages(PROJECT_ROOT)
        return

    if not args.no_build:
        build_frontend()
    run_server(host=args.host, port=args.port, static_root=PROJECT_ROOT)


if __name__ == "__main__":
    main()
