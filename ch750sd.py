#!/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd

# Imports STL files and adds them to a FreeCAD document

import sys
from pathlib import Path

import FreeCAD
import Part

from Mesh import Mesh
from Part import Shape

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
from check_stl_list import check as check_stl_list  # noqa: E402


# ---------------------------------------------------------------------------
# External FreeCAD files to insert as assembly components.
#   file        : path to the .FCStd file
#   object_name : internal Name of the object to link; the Label is also
#                 accepted, and the file's only component is used as a
#                 last resort
#   label       : tree-view label for the component
#   placement   : (x, y, z, rot_z, rot_y, rot_x) in mm and degrees
#
# Coordinates are the airframe frame the STL meshes land in: X lateral
# (left/port +, per the LEFT/RIGHT naming on the kit parts), Y vertical
# (up +; the cockpit floor sits near -1030 at the forward station), Z
# longitudinal (firewall +, around 8000, tail toward 3000).
#
# Rotations are Euler angles in degrees passed straight to FreeCAD.Rotation,
# which composes them about the LOCAL axes in Z-Y-X order.
# ---------------------------------------------------------------------------
EXTERNAL_PARTS = [
    ("ACK_E04_ELT_Bracket.FCStd", "ACK_E04_ELT_Bracket", "ELT Bracket", (334, -838.22, 5737.74, 0, 0, -90)),
    ("ACK_E04_ELT_Bracket.FCStd", "ACK_E04_ELT", "ELT", (298.98, -837.22, 5834.16, 0, 0, -90)),
    # Rudder pedal brackets, replacing the kit's C75C3-6 lateral pedal bearing
    # blocks (also in stl/). In their own file the base plate lies in local XY
    # with its normal on +Z and the rudder-tube hole runs along local Y, so a
    # half turn about the vertical axis lays the plate flat with the tube
    # running across the cabin and the mounting flange inboard; the two sides
    # differ only in the sign of rot_y.
    # The cabin floor is not level: the side-skin surface slopes up going
    # forward by 2.84 degrees, so the upright orientation is turned by that
    # angle about the aircraft lateral axis to sit the plate flush on the
    # skins. The original kit blocks measure 2.75 degrees, agreeing within the
    # noise of these coarse STLs. The resulting tilt is folded into rot_y
    # (90 - 2.836) by the Euler decomposition.
    # Y seats the plate underside flush on the floor, taken as the contact face
    # of the kit block it replaces (its lowest facet band, tilt 2.832 degrees).
    # X and Z place the plate rivet holes on the kit block's existing rivet
    # holes, so the bracket fits the existing rivet pattern. Both patterns are
    # 34.19mm apart on the two parts, confirming they are the same holes.
    # The seat is not the block's minimum Y: on a 2.8-degree slope the lowest
    # corner sits about 1.3mm below the surface at the bracket's own station,
    # so seating on the plane rather than the corner matters.
    # DO NOT "correct" this to line the bore up with the pedal shaft. The
    # bracket is rigid, and its bore-to-rivet and bore-to-plate geometry differs
    # from the kit block's by about 0.8mm in each direction, so no placement
    # satisfies bore, rivets and floor at once: centring the bore on the shaft
    # (measured 0.750/0.750 on both sides) drops the plate 0.79mm through the
    # floor and walks the rivets 0.77mm off the existing pattern. Rivet and floor
    # alignment win; the bore is left 1.06mm off. Note that this is marginal
    # rather than comfortably safe: the bracket bore is r10.5 against a tube
    # measured at r9.5 (a ring of 64 points in the kit block's own bore at this
    # station), so 1.0mm of radial clearance has to absorb 1.06mm of offset, i.e.
    # it is about 0.06mm tight. The tube itself is not in the STL set at these
    # stations, so this cannot be confirmed from these files, and a powder coat
    # on the tube makes it tighter still. Only a redesign of the bracket holes
    # would close all three constraints.
    # These two must be referenced by internal Name (Body / Body002), not by
    # the "LeftBracket"/"RightBracket" labels: the assembly also contains an
    # App::Link whose internal Name is RightBracket, so resolve_target() would
    # match that link first and produce a link pointing at a link.
    ("RudderPedalBracketAssembly.FCStd", "Body", "Rudder Pedal Bracket L", (344.498, -1032.546, 7879.352, -90, 87.164, 180)),
    ("RudderPedalBracketAssembly.FCStd", "Body002", "Rudder Pedal Bracket R", (-346.2, -1031.214, 7911.385, 90, -87.164, 180)),
    # Delrin bearing blocks, inboard of each bracket with its bore coaxial with
    # that bracket's tube hole. The source file models one bearing body and links
    # it twice, so the same is done here; the two placements differ only in
    # position, both bores running along the lateral axis.
    # These are not hand-measured. Each is the bracket placement composed with the
    # bracket-to-bearing transform measured inside the source assembly, so the
    # pair keeps the relative arrangement the source file already has while
    # spreading out to the wider bracket spacing in the airframe.
    # Coaxiality is not an assumption: the Delrin's two r2.5 bolt holes land on the
    # bracket's r2.5 bolt holes to 0.0005mm, so the Delrin is captured by the
    # bracket and the two bores are one axis. It therefore cannot be centred on
    # the tube independently of the bracket, and it inherits the bracket's
    # deliberate 1.06mm offset (see the note above).
    # That is worth knowing before ordering Delrin. The bore is r9.75 against a
    # tube measured at r9.5 from the kit block's own bore at this station, so the
    # intended clearance is 0.25mm per side, while the offset alone is 1.06mm. The
    # STL set does not include the tube at these stations, so the fit cannot be
    # confirmed from these files. Either the Delrin bore needs to open to ~10.6mm
    # to clear at the offset, or the offset has to go, which means giving up the
    # existing rivet pattern. The README already tells builders to adjust the hole
    # size, so this is a note rather than a defect in the exported geometry.
    ("RudderPedalBracketAssembly.FCStd", "Body001", "Rudder Pedal Bearing L", (326.323, -1015.062, 7878.486, 90, -87.164, -90)),
    ("RudderPedalBracketAssembly.FCStd", "Body001", "Rudder Pedal Bearing R", (-321.167, -1013.730, 7910.519, 90, -87.164, -90)),
]

# Types that make sense as an assembly component. Used by the fallback
# resolver and to filter the diagnostic listing.
COMPONENT_TYPES = (
    "App::Part",
    "PartDesign::Body",
    "Assembly::AssemblyObject",
    "Part::Feature",
    "Mesh::Feature",
    "App::Link",
)

# The assembly is built by globbing stl/, so anything on disk lands in it whether or
# not export_stl.applescript declares it. Check the two agree before doing any work:
# a silent mismatch is otherwise only noticed by someone who spots a missing part.
ok, report = check_stl_list(Path(__file__).resolve().parent)
if not ok:
    # freecadcmd discards unflushed output on sys.exit, so flush explicitly.
    print(report, file=sys.stderr, flush=True)
    sys.exit(1)
print(report, flush=True)

document_name = "ch750sd"
assembly_name = "CH750SD"


def make_placement(values):
    """(x, y, z, rz, ry, rx) in mm/degrees -> FreeCAD.Placement."""
    if values is None:
        return None
    x, y, z, rz, ry, rx = values
    return FreeCAD.Placement(
        FreeCAD.Vector(x, y, z),
        FreeCAD.Rotation(rz, ry, rx),   # constructor order is Z (yaw), Y, X (roll)
    )


def describe(document):
    """Every object in a document as Name / Label / TypeId lines."""
    return "\n".join(
        f"    {o.Name!r:32} {o.Label!r:32} {o.TypeId}" for o in document.Objects
    )


def resolve_target(source, key):
    """Resolve an object by internal Name, then by Label, then by elimination.

    getObject() matches the internal Name only, so a Label or file name
    will not be found by it.
    """
    target = source.getObject(key)
    if target is not None:
        return target, "name"

    matches = source.getObjectsByLabel(key)
    if len(matches) == 1:
        return matches[0], "label"
    if len(matches) > 1:
        raise ValueError(
            f"{len(matches)} objects in {source.FileName} share the label {key!r}; "
            f"use the internal Name instead:\n{describe(source)}"
        )

    candidates = [o for o in source.Objects if o.TypeId in COMPONENT_TYPES]
    if len(candidates) == 1:
        return candidates[0], "only component"

    raise ValueError(
        f"{key!r} is neither the Name nor the Label of an object in "
        f"{source.FileName}.\n  Objects in that file:\n{describe(source)}"
    )


def insert_external_part(document, assembly, source_document, object_name:str, label=None, placement=None):
    """Add object_name from an already-open source document to the assembly."""
    target, how = resolve_target(source_document, object_name)

    # newObject() creates the link and files it under the assembly in one step, which is what the Assembly workbench itself does.
    link = assembly.newObject("App::Link", label or target.Name)
    link.Label = label or target.Name
    link.LinkedObject = target
    link.LinkTransform = False          # the Link's own Placement wins

    if placement is not None:
        link.Placement = placement

    print(f"Linked {source_document.Name}:{target.Name} as {link.Label!r} (matched by {how})")
    return link


if document := FreeCAD.newDocument(document_name):
    assembly = document.addObject("Assembly::AssemblyObject", assembly_name)

    scaling_matrix = FreeCAD.Matrix()
    scaling_matrix.scale(1000)

    for path in Path('stl').glob('*.stl'):
        name = path.stem
        print(path.stem)
        if mesh := Mesh(str(path)):
            # eDrawings exports in meters but FreeCAD imports in millimeters
            mesh.transform(scaling_matrix)

            mesh_feature = document.addObject("Mesh::Feature", path.stem)
            mesh_feature.Mesh = mesh

            part = document.addObject("App::Part", name)
            part.Label = name
            part.addObject(mesh_feature)      # reparents the mesh/shape into the container
            assembly.addObject(part)      # the container is the assembly component

    document.recompute()

    # External links only resolve once the assembly document exists on disk, so save before creating them.
    document.saveAs(f"{document_name}.FCStd")

    source_documents = {}
    for file_path, object_name, label, placement in EXTERNAL_PARTS:
        if not (source_document := source_documents.get(Path(file_path), None)):
            source_document = FreeCAD.openDocument(file_path)
            source_documents[Path(file_path)] = source_document

        insert_external_part(document, assembly, source_document, object_name, label=label, placement=make_placement(placement))

    document.recompute()
    document.saveAs(f"{document_name}.FCStd")

    # Close the linked sources, so the script leaves a clean session.
    for open_document in FreeCAD.listDocuments().values():
        if open_document is not None and open_document is not document:
            print(f"Closing {open_document.Name}")
            FreeCAD.closeDocument(open_document.Name)

    FreeCAD.closeDocument(document.Name)
