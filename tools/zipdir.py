#!/usr/bin/env python3
"""Zip a directory, so the gerber bundle can ship as the .zip a fab expects.

`zip(1)` is not on this machine and pulling it in for one command is not worth
a package; zipfile is in the standard library.

    python3 tools/zipdir.py <dir> <out.zip>
"""
import os
import sys
import zipfile


def main():
    src, out = sys.argv[1], sys.argv[2]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(src)):
            z.write(os.path.join(src, name), name)
    print(f"wrote {out} ({os.path.getsize(out)} bytes, "
          f"{len(zipfile.ZipFile(out).namelist())} files)")


if __name__ == "__main__":
    main()
