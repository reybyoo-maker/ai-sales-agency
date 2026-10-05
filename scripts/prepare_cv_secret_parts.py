#!/usr/bin/env python3
"""Split a CV PDF into GitHub Actions-safe Base64 secret parts.

Usage:
  python scripts/prepare_cv_secret_parts.py /path/to/CV.pdf

The script writes cv_secret_part_1.txt ... cv_secret_part_7.txt in the
current directory. Each file is <= 45,000 ASCII characters.
Do not commit these generated .txt files.
"""

from __future__ import annotations

import base64
import pathlib
import sys

PARTS = 7
CHUNK_SIZE = 45_000


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/prepare_cv_secret_parts.py /path/to/CV.pdf")

    pdf_path = pathlib.Path(sys.argv[1]).expanduser()
    if not pdf_path.is_file():
        raise SystemExit(f"CV PDF tidak ditemukan: {pdf_path}")

    encoded = base64.b64encode(pdf_path.read_bytes()).decode("ascii")
    chunks = [encoded[i:i + CHUNK_SIZE] for i in range(0, len(encoded), CHUNK_SIZE)]

    if len(chunks) > PARTS:
        raise SystemExit(
            f"CV terlalu besar untuk konfigurasi {PARTS} part. "
            f"Base64 saat ini {len(encoded):,} karakter."
        )

    # Always create all seven files; empty files make it obvious when a part is missing.
    for index in range(1, PARTS + 1):
        value = chunks[index - 1] if index <= len(chunks) else ""
        pathlib.Path(f"cv_secret_part_{index}.txt").write_text(value, encoding="ascii")
        print(f"CV_PDF_BASE64_{index}: {len(value):,} characters")

    print("\nGitHub Secrets:")
    for index in range(1, PARTS + 1):
        print(f"  CV_PDF_BASE64_{index} <- cv_secret_part_{index}.txt")


if __name__ == "__main__":
    main()
