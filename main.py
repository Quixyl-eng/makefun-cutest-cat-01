#!/usr/bin/env python3
"""Emit the cutest-cat picture to the judge output path.

The picture ships next to this file as entry.png. Contest rules accept
either a PNG or a JPEG, told apart by the first bytes, and the file
name stays entry.png either way — so a JPEG payload under that name
is valid and is copied as-is. This program validates those bytes with
the Python 3.13 standard library only (the sandbox installs nothing),
then writes them unchanged to MAKEFUN_OUTPUT_DIR/entry.png, defaulting
to /output/entry.png. Both harness runs must produce identical output.

This emitter is an adaptation of the MIT-licensed cutest-dog entry at
https://github.com/Quixyl-eng/makefun-cutest-dog-02, itself following
the official make.fun cutest-cat-01 kit starter (MIT).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

MAX_BYTES = 1_048_576
MAX_EDGE = 1024
ENTRY_NAME = "entry.png"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"

# Live revision marker for the first authored write of this entrypoint.
BUILD_LABEL = "cutest-cat-live-2026-11-11"
BUILD_NOTE = "orange tabby kitten JPEG emitter; stdlib validation plus identical-copy check"


def describe_build() -> str:
    """Short banner used by --json consumers and local checks."""
    return f"{BUILD_LABEL}: {BUILD_NOTE}"


class EntryError(Exception):
    """The shipped cat picture does not meet the contest gate."""


def detect_format(data: bytes) -> str:
    if data.startswith(PNG_MAGIC):
        return "png"
    if data.startswith(JPEG_SOI):
        return "jpeg"
    raise EntryError("cat picture is neither a PNG nor a JPEG (magic bytes)")


def _png_chunk(data: bytes, offset: int) -> tuple[str, bytes, int]:
    if offset + 12 > len(data):
        raise EntryError("truncated PNG chunk header in cat picture")
    length = struct.unpack(">I", data[offset : offset + 4])[0]
    kind = data[offset + 4 : offset + 8].decode("latin-1")
    start = offset + 8
    end = start + length
    if end + 4 > len(data):
        raise EntryError(f"truncated PNG chunk {kind} in cat picture")
    payload = data[start:end]
    return kind, payload, end + 4


def png_info(data: bytes) -> dict[str, int | str]:
    if len(data) < 33 or not data.startswith(PNG_MAGIC):
        raise EntryError("invalid PNG header on cat picture")
    kind, payload, cursor = _png_chunk(data, 8)
    if kind != "IHDR" or len(payload) != 13:
        raise EntryError("cat PNG does not start with a valid IHDR")
    width, height, bit_depth, color_type, _comp, _filt, _inter = struct.unpack(
        ">IIBBBBB", payload
    )
    saw_idata = False
    saw_iend = False
    while cursor < len(data):
        kind, payload, cursor = _png_chunk(data, cursor)
        if kind == "IDAT":
            saw_idata = True
        elif kind == "IEND":
            saw_iend = True
            break
    if not saw_idata:
        raise EntryError("cat PNG has no IDAT image data")
    if not saw_iend:
        raise EntryError("cat PNG is missing the IEND end marker")
    if cursor != len(data):
        raise EntryError("trailing bytes after cat PNG IEND")
    return {
        "format": "png",
        "width": width,
        "height": height,
        "bit_depth": bit_depth,
        "color_type": color_type,
    }


def jpeg_info(data: bytes) -> dict[str, int | str]:
    if not data.startswith(JPEG_SOI) or not data.endswith(JPEG_EOI):
        raise EntryError("cat JPEG missing SOI/EOI markers")
    i = 2
    width = height = None
    while i + 3 < len(data):
        if data[i] != 0xFF:
            raise EntryError("cat JPEG marker stream is corrupt")
        while i < len(data) and data[i] == 0xFF:
            i += 1
        if i >= len(data):
            break
        marker = data[i]
        i += 1
        if marker in (0xD8, 0xD9) or marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue
        if i + 1 >= len(data):
            raise EntryError("cat JPEG truncated segment length")
        seglen = struct.unpack(">H", data[i : i + 2])[0]
        if seglen < 2 or i + seglen > len(data):
            raise EntryError("cat JPEG bad segment length")
        if marker in (0xC0, 0xC1, 0xC2) and seglen >= 7:
            height, width = struct.unpack(">HH", data[i + 3 : i + 7])
        i += seglen
        if marker == 0xDA:
            break
    if width is None or height is None:
        raise EntryError("cat JPEG has no SOF dimensions")
    return {"format": "jpeg", "width": width, "height": height}


def validate(data: bytes) -> dict[str, int | str]:
    if not data:
        raise EntryError("cat picture is empty")
    if len(data) > MAX_BYTES:
        raise EntryError(f"cat picture is {len(data)} bytes; max is {MAX_BYTES}")
    fmt = detect_format(data)
    info = png_info(data) if fmt == "png" else jpeg_info(data)
    w, h = int(info["width"]), int(info["height"])
    if w > MAX_EDGE or h > MAX_EDGE:
        raise EntryError(f"cat picture is {w}x{h}; max edge is {MAX_EDGE}")
    if w < 1 or h < 1:
        raise EntryError("cat picture has non-positive dimensions")
    info["bytes"] = len(data)
    info["sha256"] = hashlib.sha256(data).hexdigest()
    return info


def resolve_source(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    return Path(__file__).resolve().parent / ENTRY_NAME


def resolve_output_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    env = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if env:
        return Path(env)
    return Path("/output")


def verify_copy(source: Path, dest: Path) -> None:
    """Both harness runs must write identical bytes; confirm the copy matches the source."""
    if source.read_bytes() != dest.read_bytes():
        raise EntryError("copied cat picture does not match the source bytes")


def emit(source: Path, output_dir: Path) -> dict[str, int | str]:
    data = source.read_bytes()
    info = validate(data)
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / ENTRY_NAME
    dest.write_bytes(data)
    verify_copy(source, dest)
    info["source"] = str(source)
    info["output"] = str(dest)
    return info


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Copy the cutest-cat entry.png into the judge output dir.")
    p.add_argument("--check", action="store_true", help="validate only; do not write output")
    p.add_argument("--source", type=Path, default=None, help="path to entry.png (default: beside this file)")
    p.add_argument("--output-dir", type=Path, default=None, help="override MAKEFUN_OUTPUT_DIR / /output")
    p.add_argument("--json", action="store_true", help="print validation info as JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = resolve_source(args.source)
    try:
        if not source.is_file():
            raise EntryError(f"missing cat picture at {source}")
        if args.check:
            info = validate(source.read_bytes())
            info["source"] = str(source)
        else:
            info = emit(source, resolve_output_dir(args.output_dir))
    except EntryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        info = dict(info)
        info["build"] = describe_build()
        print(json.dumps(info, sort_keys=True))
    else:
        print(
            f"ok {info['format']} {info['width']}x{info['height']} "
            f"{info['bytes']} bytes sha256={info['sha256'][:12]}…"
        )
        if "output" in info:
            print(f"wrote {info['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
