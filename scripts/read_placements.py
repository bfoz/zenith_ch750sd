#!/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd

"""Print the current placement of every external part in ch750sd.FCStd as a
ready-to-paste EXTERNAL_PARTS tuple.

Positioning these parts is easier by dragging them in the FreeCAD GUI than by
describing them in words. Drag the links in ch750sd.FCStd until they look right,
save, run this, and the tuples it prints are what ch750sd.py needs. It writes
nothing: the tuples go into EXTERNAL_PARTS by hand so the derivation comments
next to each entry stay intact.

    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd scripts/read_placements.py

Results also go to placements.txt, because freecadcmd buries stdout under
progress spam from opening the document.

Only App::Links are reported, which is what every externally placed part in the
reference assembly is. Airframe STL meshes are placed by the file itself and are
not editable this way.
"""

import os
import sys
import traceback

import FreeCAD

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fmt(v):
    """Trim to 4 dp and drop trailing zeros, so tuples stay readable."""
    s = "%.4f" % v
    return s.rstrip("0").rstrip(".") if "." in s else s


def collect(path):
    doc = FreeCAD.openDocument(path)
    rows = []
    try:
        for link in doc.Objects:
            if link.TypeId != "App::Link":
                continue
            target = link.LinkedObject
            src = "?"
            name = "?"
            if target is not None:
                name = target.Name
                if target.Document is not None:
                    src = os.path.basename(target.Document.FileName) or "?"
            pl = link.Placement
            yaw, pitch, roll = pl.Rotation.toEuler()
            rows.append((src, name, link.Label,
                         (pl.Base.x, pl.Base.y, pl.Base.z, yaw, pitch, roll)))
    finally:
        FreeCAD.closeDocument(doc.Name)
    return rows


def render(rows):
    out = ["# Paste these into EXTERNAL_PARTS in ch750sd.py",
           "# fields: file, object Name, tree label, placement",
           "# placement = (x, y, z, rot_z, rot_y, rot_x) in mm and degrees",
           ""]
    sources = sorted({r[0] for r in rows})
    for src in sources:
        out.append("# from %s" % src)
        for _, name, label, t in [r for r in rows if r[0] == src]:
            out.append('    ("%s", "%s", "%s", (%s)),'
                       % (src, name, label, ", ".join(fmt(v) for v in t)))
        out.append("")

    # A link left at the origin usually means a drag dropped it.
    notes = ["# sanity checks"]
    for _, _, label, t in rows:
        if (abs(t[0]) + abs(t[1]) + abs(t[2])) < 1.0:
            notes.append("#   %s: at the origin - did the drag lose it?" % label)
    if len(notes) > 1:
        out.extend(notes)

    out.append("# reminder: the Elevator Pulley Bracket / Base / Pulley links are one unit.")
    out.append("# Drag all three of a side together, or move just the bracket and base and")
    out.append("# say so - the pulley placement is the unit placement composed with its")
    out.append("# internal offset (0, 0.0625, 27.5) Euler (90,0,0), so it can be recomputed")
    out.append("# rather than measured. Same for the rudder pedal bearing and its bracket.")
    return "\n".join(out) + "\n"


def main():
    path = os.path.join(ROOT, "ch750sd.FCStd")
    if not os.path.isfile(path):
        sys.stderr.write("not found: %s\nBuild it first: freecadcmd ch750sd.py\n" % path)
        sys.stderr.flush()
        return 1
    try:
        text = render(collect(path))
    except Exception:
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
        return 1

    report = os.path.join(ROOT, "placements.txt")
    with open(report, "w") as fh:
        fh.write(text)
    sys.stdout.write(text)
    sys.stdout.flush()
    sys.stderr.write("\nWrote %s\n" % report)
    sys.stderr.flush()
    return 0


# freecadcmd does not set __name__ to "__main__" and swallows uncaught exceptions
# with exit code 0, so call directly and exit explicitly.
sys.exit(main())
