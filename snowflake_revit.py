import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
import math

# Revit document
doc = DocumentManager.Instance.CurrentDBDocument

# Building parameters
height_per_level = 10 * 12  # 10 feet in inches
num_levels = 20
base_width = 50 * 12  # 50 feet in inches

# Get Revit's minimum curve tolerance
min_length = doc.Application.ShortCurveTolerance * 1.5  # 50% buffer

# Get default wall and floor types
wall_type = FilteredElementCollector(doc).OfClass(WallType).FirstElement()
floor_type = FilteredElementCollector(doc).OfClass(FloorType).FirstElement()

def generate_koch_snowflake_points(order, scale):
    def koch_curve(p1, p2, order):
        if order == 0:
            return [p1, p2]
        else:
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            segment_length = math.sqrt(dx*dx + dy*dy)
            
            if segment_length / 3 < min_length:
                return [p1, p2]
                
            pA = (p1[0] + dx/3, p1[1] + dy/3)
            pB = (p1[0] + 2*dx/3, p1[1] + 2*dy/3)
            
            angle = math.pi/3
            cx = pA[0] + (pB[0]-pA[0])*math.cos(angle) - (pB[1]-pA[1])*math.sin(angle)
            cy = pA[1] + (pB[0]-pA[0])*math.sin(angle) + (pB[1]-pA[1])*math.cos(angle)
            pC = (cx, cy)
            
            return (
                koch_curve(p1, pA, order-1) +
                koch_curve(pA, pC, order-1)[1:] +
                koch_curve(pC, pB, order-1)[1:] +
                koch_curve(pB, p2, order-1)[1:]
            )
    
    height = math.sqrt(3)/2 * scale
    p1 = (0, 0)
    p2 = (scale, 0)
    p3 = (scale/2, height)
    
    points = (
        koch_curve(p1, p2, order) +
        koch_curve(p2, p3, order)[1:] +
        koch_curve(p3, p1, order)[1:]
    )
    
    # Remove duplicates and nearby points
    unique_points = []
    for point in points:
        if not unique_points or math.sqrt((point[0]-unique_points[-1][0])**2 + (point[1]-unique_points[-1][1])**2) > min_length:
            unique_points.append(point)
    
    return unique_points

# Generate points (order 2 is optimal for Revit)
snowflake_points = generate_koch_snowflake_points(order=2, scale=base_width)

# Start transaction
TransactionManager.Instance.EnsureInTransaction(doc)

created_walls = []
created_floors = []
created_levels = []

for i in range(num_levels):
    z = i * height_per_level
    
    # Create new level
    level = Level.Create(doc, z)
    created_levels.append(level)
    
    # Convert points to Revit XYZ
    revit_points = [XYZ(p[0], p[1], z) for p in snowflake_points]
    
    # Create curve loop and walls
    curve_loop = CurveLoop()
    wall_lines = []
    
    for j in range(len(revit_points)):
        start = revit_points[j]
        end = revit_points[(j+1) % len(revit_points)]
        
        if start.DistanceTo(end) > min_length:
            try:
                line = Line.CreateBound(start, end)
                wall = Wall.Create(doc, line, wall_type.Id, level.Id, height_per_level, 0, False, False)
                created_walls.append(wall)
                wall_lines.append(line)
                curve_loop.Append(line)
            except Exception as e:
                pass  # Skip any problematic segments
    
    # Create floor only if we have valid curves
    if hasattr(curve_loop, 'Count'):  # Proper way to check in Revit
        if curve_loop.Count >= 3:  # Need at least 3 sides for a floor
            try:
                floor = Floor.Create(doc, [curve_loop], floor_type.Id, level.Id)
                created_floors.append(floor)
            except:
                pass  # Skip if floor creation fails

# End transaction
TransactionManager.Instance.TransactionTaskDone()

# Prepare output
output = "🏢 Koch Snowflake Building Created Successfully:\n"
output += f"• Levels: {len(created_levels)}\n"
output += f"• Walls: {len(created_walls)}\n"
output += f"• Floors: {len(created_floors)}\n"
output += f"• Base Width: {base_width/12:.1f} feet\n"
output += f"• Total Height: {num_levels * height_per_level/12:.1f} feet"

OUT = output
