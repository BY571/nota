"""CLI entry point for nota."""

import argparse
import os
import sys
import webbrowser
from threading import Timer

from nota.server import app, configure


def main():
    parser = argparse.ArgumentParser(
        prog="nota",
        description="View and annotate rendered Markdown files in the browser",
    )
    parser.add_argument("file", help="Markdown file to annotate")
    parser.add_argument("--port", type=int, default=5050, help="Port (default: 5050)")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    md_file = os.path.abspath(args.file)
    if not os.path.exists(md_file):
        print(f"File not found: {md_file}")
        sys.exit(1)

    configure(md_file)

    print(f"  File: {md_file}")
    print(f"  Annotations: {md_file}.nota.json")
    print(f"  URL: http://localhost:{args.port}")
    print()
    print("  Select text to annotate. Ctrl+C to quit.")

    if not args.no_open:
        Timer(1.0, lambda: webbrowser.open(f"http://localhost:{args.port}")).start()

    app.run(port=args.port, debug=False)
