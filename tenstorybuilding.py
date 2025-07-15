import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

# Revit document
doc = DocumentManager.Instance.CurrentDBDocument

# Building dimensions (in inches)
width = 15 * 12
depth = 15 * 12
height_per_level = 8 * 12
num_levels = 10

# Get default wall and floor types
wall_type = FilteredElementCollector(doc).OfClass(WallType).FirstElement()
floor_type = FilteredElementCollector(doc).OfClass(FloorType).FirstElement()

# Base point
origin = XYZ(0, 0, 0)

# Start transaction
TransactionManager.Instance.EnsureInTransaction(doc)

created_walls = []
created_floors = []
created_levels = []

for i in range(num_levels):
    z = i * height_per_level

    # Create new level at each height
    level = Level.Create(doc, z)
    created_levels.append(level)

    # Define 4 corner points of rectangle
    pt1 = XYZ(0, 0, z)
    pt2 = XYZ(width, 0, z)
    pt3 = XYZ(width, depth, z)
    pt4 = XYZ(0, depth, z)

    # Create boundary lines
    lines = [
        Line.CreateBound(pt1, pt2),
        Line.CreateBound(pt2, pt3),
        Line.CreateBound(pt3, pt4),
        Line.CreateBound(pt4, pt1)
    ]

    # Create walls
    for line in lines:
        wall = Wall.Create(doc, line, wall_type.Id, level.Id, height_per_level, 0, False, False)
        created_walls.append(wall)

    # Create floor slab
    curve_loop = CurveLoop()
    for line in lines:
        curve_loop.Append(line)

    floor = Floor.Create(doc, [curve_loop], floor_type.Id, level.Id)
    created_floors.append(floor)

# End transaction
TransactionManager.Instance.TransactionTaskDone()

# Output message
OUT = f"✅ Created {len(created_levels)} levels, {len(created_walls)} walls, and {len(created_floors)} floors."
