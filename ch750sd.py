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
    # blocks. Those kit blocks are deliberately not exported to stl/ any more (see
    # the note in export_stl.applescript), so the assembly shows the as-built
    # parts at this station.
    # Because the meshes are gone, the absolute pose they supplied as the datum for
    # the placement below is recorded here, in the coordinate system the meshes land
    # in (the same one these placements are written in). Both measure about 25.4mm
    # along X, 40.0mm in Y and 55.9mm in Z:
    #   L  X  330.83.. 356.25  Y -1033.87.. -993.92  Z 7851.66.. 7907.53
    #   R  X -356.88..-331.48  Y -1032.54.. -992.58  Z 7883.69.. 7939.56
    # Every figure quoted in the rest of this comment block was measured from those
    # two meshes. To re-derive anything here, re-export them and check against the
    # boxes above before trusting the result. The C75C3-3 pedal meshes are still
    # exported, so the pedal-axis side of the derivation can always be re-checked.
    # In their own file the base plate lies in local XY
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
    # Elevator pulley brackets, on the cabin floor just forward of the jump seat
    # rear channel (LS75F33-1, web at Z 6088..6095, bottom flange reaching Z 6113).
    #
    # Each unit is three links, not one. Linking the source document's Assembly
    # object looked attractive because it carries the reference pulley inside the
    # unit, and it loads fine headless, but in the GUI both links came up "Link not
    # restored" and rendered nothing. Linking the PartDesign bodies instead, which
    # is what the rudder pedal entries above already do and which does restore.
    # The three bodies of one unit do NOT share a placement. Inside the source
    # Assembly the Bracket (Name Body) and Base (Name Body001) links are both at
    # identity and the Pulley (Name Body002) link is at Base=(0, 0.0625, 27.5)
    # Euler=(90,0,0), but here the bracket sits on top of the floor skin and the
    # base plate goes under it, so they cannot be coaxial. The Bracket tuple is the
    # unit placement, the Pulley tuple is that composed with the link offset above
    # rather than being measured by hand, and the Base tuple is the unit placement
    # slid along the floor normal to the underside. See the skin note below.
    #
    # Orientation. The base plate lies in local XY with the 50mm upright on local Z,
    # so local X -> along the floor fore-aft, local Y -> lateral, local Z -> the
    # floor normal stands the bracket up with its pulley axis lateral, which is what
    # a fore-aft elevator cable needs.
    # The floor is NOT level. Least squares over the LS75F1-1 bottom skin from
    # Z 5950 to 6350 (6484 points, rms 0.26mm) gives
    #     Y = +0.000338*X - 0.214355*Z + 350.6
    # which drops 0.214mm per mm forward: 12.101 degrees of rake. Rotating the
    # level-floor orientation by that much about the aircraft X axis brings the
    # plate normal from (0,1,0) to (0, 0.97779, 0.20959), flush on the floor. The
    # right-hand unit is the left turned 180 degrees about the vertical (a mirror is
    # not a rotation), and costs nothing since the unit is nearly symmetric about
    # local Y.
    #
    # THE FIT IS THE SKIN MIDPLANE, NOT ITS UPPER SURFACE. A least-squares over all
    # of a mesh's points averages the two faces, so this plane runs through the
    # middle of the bottom skin, not along the surface a builder would put a part
    # on. Measuring the skin LS75F1-1 in this neighbourhood gives thickness 0.5080mm
    # (0.020in), with its two faces as tight 599-point clusters at
    #     cabin (upper) face     h = +0.2361
    #     outside (lower) face   h = -0.2719
    # above the fitted plane, where h is signed height along the floor normal,
    # positive into the cabin. Refitting locally over the skin points in each plate's
    # own X band returns the same plane and the same thickness, which matters because
    # the skin STL happens to have no sampled points inside either plate footprint.
    #
    # So the two parts of the unit are placed relative to the two skin faces:
    # the bracket's lowest material rests on the CABIN face (lifted 0.2361mm along
    # the floor normal from the fit), and the base plate's cabin-facing face is
    # tangent to the OUTSIDE face, so the plate occupies h -1.29..-0.27 and the
    # 0.508mm skin sits in the clamp between plate and bracket. Before this both
    # bodies were put on the midplane and so each bit into the skin. README step 9
    # says the base plates can be installed inside or outside, purely aesthetic; this
    # assembly depicts them outside, which is also how step 10 rivets them.
    #
    # Y = floor_y(X, Z) from the fit above plus the h offset each body needs. Note
    # the plate's own Y extent then comes out at about 11.5mm, not 1mm: it spans
    # 50mm along a 12-degree slope. That is correct, not a sign the plate is
    # standing on end.
    #
    # X aligns each pulley with the elevator cable bearing set into the channel web
    # directly above it: a pulley must sit in the plane of the cable running over it
    # or the cable skews off the groove, so the pulley's X is its bearing's X. Those
    # are the LS75C34-5 ELEVATOR CABLE BEARING - JUMPSEAT parts in stl/, centres
    # X +46.18 and -53.49, Y -926.4 and -929.8, Z 6085.45. Spacing 99.67mm, and the
    # two share a Z to 0.01mm, so the pair is symmetric fore-aft with only a ~3.5mm
    # offset each way about the centreline. Measured to the sheave centres the
    # bearings then stand 57.5mm aft of and 11.4mm (left) / 8.0mm (right) above
    # them, so the cables descend onto the grooves at 11 and 8 degrees, which is
    # the arrangement in the photograph. The two angles differ only because the
    # bearings themselves are 3.4mm apart in Y, not because the units are placed
    # differently; the brackets are mirror images of one placement.
    #
    # The C75C4-3 parts used here before are RUDDER cable fair leads, exported by
    # mistake. Their centres (X +68.67 and -76.33, 145mm apart, 35x35mm pads 3.4mm
    # thick in the web plane at Z 6088..6095) are still in stl/ and still modelled,
    # because they belong to the airframe, but they are not this bracket's datum.
    #
    # The four big 183mm openings, at X -364.5, -180.5, +174.5 and +358.5, are also
    # NOT cable routes and were a wrong guess. Putting the pulleys on them gave 355mm
    # spacing, far too wide, and the cable bearings lie in the web material between
    # them rather than inside any opening. Earlier notes here debating which pair of
    # big openings the cables use were asking the wrong question.
    #
    # Station (Z) butts the bracket's aft end against the forward face of the
    # channel's lower flange (the lip at Y -959.5..-950 that projects forward to
    # Z 6112.75). That face is perpendicular to the fore-aft axis, read from the STL
    # facets: it stands at Z 6112.751 across the left bracket's X span and 6112.763
    # across the right's, so each side gets its own station. The station is solved
    # iteratively against the solid rather than computed as face + 24.445mm, because
    # lifting the unit onto the cabin face along the floor normal also raises Z by
    # 0.0495mm, and the contacting point is the lowest point of the upright's foot,
    # not the plate centre.
    # Verified by transforming every channel and skin point into each body's local
    # frame and querying the B-rep with isInside (validated first with positive and
    # negative controls on this geometry): zero points inside any of the six solids.
    # The skin is clamped between the two plates with no penetration of either.
    # distToShape against the channel mesh vertices, which is a stricter test than
    # the point-membership sweep, gives the bracket foot 0.235mm (L) / 0.234mm (R)
    # from the channel and the base plate 0.648mm (L) / 0.642mm (R). Treat those as
    # the honest clearances rather than claiming contact: the flange's forward-most
    # material varies over the lip band by a few tenths of a millimetre (Z 6112.54
    # at the outboard edge of the lip, 6112.763 further inboard), so "touching" is
    # inside the resolution of the airframe mesh here.
    # Worth flagging to anyone who moves this again: dropping the base plate under
    # the skin carries its aft end past the flange face too, because the station is
    # constrained by the bracket's foot. The plate ends up passing 0.64mm below the
    # channel lip. That is clear of the mesh as modelled, but it is a tight margin
    # against a formed channel, and a real part may want the plate's aft corner
    # cleared or the station brought forward.
    # Earlier here the station came from plate centre = flange face + 24.445mm with
    # the unit left on the midplane, which put 0.236mm of both bodies inside the
    # skin; before that the centre sat at 6142.245, a 5mm design gap rather than
    # contact.
    # The bracket base Z values below happen to land on 6137.196 and 6137.208 again,
    # the same to 3dp as the pre-lift numbers. Not a coincidence to lean on: the
    # solved station is 6137.146 and 6137.158, and the lift adds 0.0495mm of Z.
    ("ElevatorPulleyBracket.FCStd", "Body", "Elevator Pulley Bracket L", (46.18, -964.679, 6137.196, -90, -77.9014, 0)),
    ("ElevatorPulleyBracket.FCStd", "Body001", "Elevator Pulley Base L", (46.18, -966.166, 6136.877, -90, -77.9014, 0)),
    ("ElevatorPulleyBracket.FCStd", "Body002", "Elevator Pulley L", (46.242, -937.789, 6142.96, 0, 0, -77.9014)),
    ("ElevatorPulleyBracket.FCStd", "Body", "Elevator Pulley Bracket R", (-53.49, -964.715, 6137.208, 90, 77.9014, 0)),
    ("ElevatorPulleyBracket.FCStd", "Body001", "Elevator Pulley Base R", (-53.49, -966.202, 6136.889, 90, 77.9014, 0)),
    ("ElevatorPulleyBracket.FCStd", "Body002", "Elevator Pulley R", (-53.553, -937.826, 6142.972, -180, 0, 77.9014)),
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
