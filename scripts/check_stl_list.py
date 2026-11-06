"""Guard against drift between export_stl.applescript's part_list and stl/.

ch750sd.py builds the reference assembly by globbing stl/*.stl, so a mesh that is
on disk but absent from part_list still lands in the assembly, and a part listed
but never exported simply is not there. Neither is reported by anything else, which
is how thirteen meshes ended up exported by hand and missing from the list.

This compares the two and fails on any difference. It is deliberately pure stdlib
so it runs without FreeCAD and without macOS.

Used by ch750sd.py (which fails before building) and by `make check-stl`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

APPLESCRIPT = "export_stl.applescript"
STL_DIR = "stl"

# Continuation mark (option-L) used to wrap the list across lines.
CONTINUATION = "\u00ac"


def part_list(script_path: Path) -> list[str]:
    """The part names declared in part_list, in file order.

    Raises ValueError if the list cannot be found, so a refactor that moves or
    renames it fails loudly instead of reading as an empty list.
    """
    text = script_path.read_text(encoding="utf-8")

    start = text.find("set part_list to {")
    if start == -1:
        raise ValueError(
            f"{script_path}: could not find 'set part_list to {{'; "
            "if the list was renamed, update scripts/check_stl_list.py"
        )

    # Take the block up to the closing brace of the list. AppleScript has no
    # nested braces here, so the first one ends it.
    end = text.find("}", start)
    if end == -1:
        raise ValueError(f"{script_path}: part_list has no closing brace")

    block = text[start:end]

    # -- comments run to end of line and are not part of the list.
    lines = [re.sub(r"--.*$", "", line) for line in block.splitlines()]
    joined = "\n".join(line.replace(CONTINUATION, " ") for line in lines)

    return re.findall(r'"([^"]+)"', joined)


def stl_files(stl_dir: Path) -> list[str]:
    return sorted(path.stem for path in stl_dir.glob("*.stl"))


def compare(names: list[str], files: list[str]) -> tuple[list[str], list[str]]:
    """(in list but not on disk, on disk but not in list)."""
    listed, present = set(names), set(files)
    return sorted(listed - present), sorted(present - listed)


def check(root: Path) -> tuple[bool, str]:
    """Returns (ok, report). ok is True when the two agree or there is nothing to check."""
    script_path = root / APPLESCRIPT
    stl_dir = root / STL_DIR

    if not script_path.is_file():
        return False, f"{script_path}: not found"

    try:
        names = part_list(script_path)
    except ValueError as exc:
        return False, str(exc)

    if not names:
        return False, f"{script_path}: part_list is empty"

    if not stl_dir.is_dir():
        return True, (
            f"{STL_DIR}/ is absent (nothing exported yet); "
            f"part_list declares {len(names)} parts"
        )

    files = stl_files(stl_dir)
    missing_files, missing_entries = compare(names, files)

    if not missing_files and not missing_entries:
        return True, f"part_list and {STL_DIR}/ agree ({len(names)} parts)"

    lines = [f"part_list and {STL_DIR}/ disagree:"]
    for name in missing_files:
        lines.append(f"  listed but not exported: {name}")
    for name in missing_entries:
        lines.append(f"  exported but not in part_list: {name}")
    lines.append("")
    lines.append(
        "part_list is the source of truth for the airframe meshes. Either export\n"
        f"  the missing parts with {APPLESCRIPT}, or remove their lines from\n"
        "  part_list. If a part was exported by hand, add it to part_list so the\n"
        "  next run regenerates it."
    )
    return False, "\n".join(lines)


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    ok, report = check(root)
    print(report, file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
