import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
from System.Collections.Generic import List

# ---------------------------------------------
# Revit document
# ---------------------------------------------
doc = DocumentManager.Instance.CurrentDBDocument

# ---------------------------------------------
# Units helper (your dims are in INCHES; Revit expects FEET)
# ---------------------------------------------
TOFT = 1.0 / 12.0

# ---------------------------------------------
# Exeter Library - simplified key dimensions (in inches)
# ---------------------------------------------
BUILDING_SIZE = 111 * 12          # 111 ft square footprint (in)
TOTAL_HEIGHT  = 80  * 12          # 80 ft overall height (in)
NUM_LEVELS    = 5                 # 5 main levels
HEIGHT_PER_LEVEL = TOTAL_HEIGHT / float(NUM_LEVELS)

ATRIUM_SIZE   = 32  * 12          # ~32 ft square central void (in)

# Derived helpers (still inches here)
W = BUILDING_SIZE
D = BUILDING_SIZE                  # square
half_atrium = ATRIUM_SIZE / 2.0
center_x = W / 2.0
center_y = D / 2.0

# ---------------------------------------------
# Types
# ---------------------------------------------
wall_type  = FilteredElementCollector(doc).OfClass(WallType).FirstElement()
floor_type = FilteredElementCollector(doc).OfClass(FloorType).FirstElement()

if wall_type is None or floor_type is None:
    raise Exception("Missing a WallType or FloorType in this project.")

# ---------------------------------------------
# Transaction
# ---------------------------------------------
TransactionManager.Instance.EnsureInTransaction(doc)

created_levels = []
created_walls  = []
created_floors = []

# Make levels (ground at z=0)  -- convert z to FEET
for i in range(NUM_LEVELS):
    z_in = i * HEIGHT_PER_LEVEL
    z = z_in * TOFT
    lvl = Level.Create(doc, z)
    created_levels.append(lvl)

    # --- Perimeter rectangle (convert XY to FEET)
    p1 = XYZ(0 * TOFT,   0 * TOFT,   z)
    p2 = XYZ(W * TOFT,   0 * TOFT,   z)
    p3 = XYZ(W * TOFT,   D * TOFT,   z)
    p4 = XYZ(0 * TOFT,   D * TOFT,   z)

    outer_lines = [
        Line.CreateBound(p1, p2),
        Line.CreateBound(p2, p3),
        Line.CreateBound(p3, p4),
        Line.CreateBound(p4, p1)
    ]

    # --- Create perimeter walls for this level (height in FEET)
    level_height_ft = (HEIGHT_PER_LEVEL * TOFT)
    for ln in outer_lines:
        w = Wall.Create(doc, ln, wall_type.Id, lvl.Id,
                        level_height_ft, 0.0, False, False)
        created_walls.append(w)

    # --- Floor profile: outer boundary + inner hole for atrium
    # Use CurveLoops and ensure the inner loop is REVERSED to form a hole
    outer = CurveLoop()
    for ln in outer_lines:
        outer.Append(ln)

    # Inner (atrium) square centered, coords in FEET
    ax1 = XYZ((center_x - half_atrium) * TOFT, (center_y - half_atrium) * TOFT, z)
    ax2 = XYZ((center_x + half_atrium) * TOFT, (center_y - half_atrium) * TOFT, z)
    ax3 = XYZ((center_x + half_atrium) * TOFT, (center_y + half_atrium) * TOFT, z)
    ax4 = XYZ((center_x - half_atrium) * TOFT, (center_y + half_atrium) * TOFT, z)

    # Reverse order to opposite orientation (cuts an opening)
    inner = CurveLoop()
    inner.Append(Line.CreateBound(ax4, ax3))
    inner.Append(Line.CreateBound(ax3, ax2))
    inner.Append(Line.CreateBound(ax2, ax1))
    inner.Append(Line.CreateBound(ax1, ax4))

    # Create "donut" floor (outer loop + inner opening loop)
    floor = Floor.Create(doc, List[CurveLoop]([outer, inner]), floor_type.Id, lvl.Id)
    created_floors.append(floor)

TransactionManager.Instance.TransactionTaskDone()

OUT = (
    "✅ Simplified Exeter Library created — "
    f"{len(created_levels)} levels (each {HEIGHT_PER_LEVEL*TOFT:.1f} ft), "
    f"{len(created_walls)} perimeter walls, {len(created_floors)} donut floors, "
    f"footprint {BUILDING_SIZE*TOFT:.0f}×{BUILDING_SIZE*TOFT:.0f} ft with a "
    f"{ATRIUM_SIZE*TOFT:.0f} ft square atrium."
)
