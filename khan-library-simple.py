import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

# ---------------------------------------------
# Revit document
# ---------------------------------------------
doc = DocumentManager.Instance.CurrentDBDocument

# ---------------------------------------------
# Exeter Library - simplified key dimensions (in inches)
# ---------------------------------------------
BUILDING_SIZE = 111 * 12          # 111 ft square footprint
TOTAL_HEIGHT  = 80 * 12           # 80 ft overall height
NUM_LEVELS    = 5                 # 5 main levels
HEIGHT_PER_LEVEL = TOTAL_HEIGHT / float(NUM_LEVELS)

ATRIUM_SIZE   = 32 * 12           # ~32 ft square central void (through all floors)

# Derived helpers
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

# ---------------------------------------------
# Transaction
# ---------------------------------------------
TransactionManager.Instance.EnsureInTransaction(doc)

created_levels = []
created_walls  = []
created_floors = []

# Make levels (ground at z=0)
for i in range(NUM_LEVELS):
    z = i * HEIGHT_PER_LEVEL
    lvl = Level.Create(doc, z)
    created_levels.append(lvl)

    # --- Perimeter rectangle (0,0) to (W,D) at elevation z
    p1 = XYZ(0, 0, z)
    p2 = XYZ(W, 0, z)
    p3 = XYZ(W, D, z)
    p4 = XYZ(0, D, z)

    outer_lines = [
        Line.CreateBound(p1, p2),
        Line.CreateBound(p2, p3),
        Line.CreateBound(p3, p4),
        Line.CreateBound(p4, p1)
    ]

    # --- Create perimeter walls for this level (rising one level)
    for ln in outer_lines:
        w = Wall.Create(doc, ln, wall_type.Id, lvl.Id,
                        HEIGHT_PER_LEVEL, 0.0, False, False)
        created_walls.append(w)

    # --- Floor profile: outer boundary + inner hole for atrium
    outer = CurveLoop()
    for ln in outer_lines:
        outer.Append(ln)

    # Inner (atrium) square centered
    ax1 = XYZ(center_x - half_atrium, center_y - half_atrium, z)
    ax2 = XYZ(center_x + half_atrium, center_y - half_atrium, z)
    ax3 = XYZ(center_x + half_atrium, center_y + half_atrium, z)
    ax4 = XYZ(center_x - half_atrium, center_y + half_atrium, z)

    inner = CurveLoop()
    inner.Append(Line.CreateBound(ax1, ax2))
    inner.Append(Line.CreateBound(ax2, ax3))
    inner.Append(Line.CreateBound(ax3, ax4))
    inner.Append(Line.CreateBound(ax4, ax1))

    # Create "donut" floor (outer loop with an opening loop)
    floor = Floor.Create(doc, [outer, inner], floor_type.Id, lvl.Id)
    created_floors.append(floor)

TransactionManager.Instance.TransactionTaskDone()

OUT = (
    "✅ Simplified Exeter Library created — "
    f"{len(created_levels)} levels (each {HEIGHT_PER_LEVEL/12:.1f} ft), "
    f"{len(created_walls)} perimeter walls, {len(created_floors)} donut floors, "
    f"footprint {BUILDING_SIZE/12:.0f}×{BUILDING_SIZE/12:.0f} ft with a "
    f"{ATRIUM_SIZE/12:.0f} ft square atrium."
)
