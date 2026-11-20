"""news-image-20261120 entry.

Writes the front page for Friday 20 November 2026 to the output folder.
The page itself ships in this repository as entry.png; this script checks
that the file is a complete PNG (its signature, every chunk's checksum,
the header size and the 1 MiB cap) and then writes a copy straight into
the output folder, with no temporary file: the grader reads the output
folder as another user, so a hidden temp file or a 0600 mode there breaks
its output rules. It reads no clock, no network and no random source, so
two runs produce the same file.
"""

import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

SOURCE = "entry.png"
MAX_BYTES = 1_048_576
MAX_SIDE = 1024
SIGNATURE = b"\x89PNG\r\n\x1a\n"


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_source():
    path = Path(__file__).resolve().parent / SOURCE
    try:
        data = path.read_bytes()
    except OSError as exc:
        fail(f"cannot read {path}: {exc}")
    if len(data) > MAX_BYTES:
        fail(f"{SOURCE} is {len(data)} bytes; the cap is {MAX_BYTES}")
    if data[:8] != SIGNATURE:
        fail(f"{SOURCE} does not start with the PNG signature")
    return data


def check_chunks(data):
    """Walk every chunk, verifying CRCs; return the IHDR dimensions."""
    pos = 8
    seen = set()
    width = height = None
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        end = pos + 8 + length + 4
        if end > len(data):
            fail(f"chunk {kind!r} runs past the end of the file")
        body = data[pos + 8:end - 4]
        crc_input = data[pos + 4:end - 4]
        stored = struct.unpack(">I", data[end - 4:end])[0]
        if zlib.crc32(crc_input) & 0xFFFFFFFF != stored:
            fail(f"chunk {kind!r} fails its CRC check")
        name = kind.decode("latin-1")
        seen.add(name)
        if name == "IHDR":
            if length != 13:
                fail(f"IHDR chunk is {length} bytes; it must be 13")
            width, height = struct.unpack(">II", body[:8])
        pos = end
        if name == "IEND":
            break
    if "IHDR" not in seen:
        fail("no IHDR chunk found")
    if "IEND" not in seen:
        fail("no IEND chunk found")
    if pos != len(data):
        fail("trailing bytes after the IEND chunk")
    if not (1 <= width <= MAX_SIDE and 1 <= height <= MAX_SIDE):
        fail(f"image is {width}x{height}; the cap is {MAX_SIDE}x{MAX_SIDE}")
    return width, height


def place(data, width, height):
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / SOURCE
    target.write_bytes(data)
    # Explicit mode: the grader reads /output as another user, and the
    # ambient umask is not guaranteed, so do not leave it to chance.
    os.chmod(target, 0o644)
    after = target.read_bytes()
    if hashlib.sha256(after).hexdigest() != hashlib.sha256(data).hexdigest():
        fail(f"{target} came out different from the source")
    print(f"wrote {target} ({width}x{height}, {len(data)} bytes)")


def main():
    data = read_source()
    width, height = check_chunks(data)
    place(data, width, height)


if __name__ == "__main__":
    main()
