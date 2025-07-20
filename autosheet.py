import clr
clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

# Revit doc access
doc = DocumentManager.Instance.CurrentDBDocument

# STEP 1: Find first title block available
titleblock_symbol = FilteredElementCollector(doc)\
    .OfClass(FamilySymbol)\
    .OfCategory(BuiltInCategory.OST_TitleBlocks)\
    .FirstElement()

# Check
if not titleblock_symbol:
    OUT = "⚠️ No title block found."
else:
    # STEP 2: Begin transaction
    TransactionManager.Instance.EnsureInTransaction(doc)

    # Activate the type if needed
    if not titleblock_symbol.IsActive:
        titleblock_symbol.Activate()
        doc.Regenerate()

    # STEP 3: Change Width & Height if parameters exist
    for param in titleblock_symbol.Parameters:
        if param.Definition.Name == "Width":
            param.Set(14.813)  # Inches
        if param.Definition.Name == "Height":
            param.Set(8.813)   # Inches

    # STEP 4: Create new sheet
    sheet = ViewSheet.Create(doc, titleblock_symbol.Id)
    sheet.SheetNumber = "PORT-EVA"
    sheet.Name = "Portfolio AutoSheet"

    # Finalize
    TransactionManager.Instance.TransactionTaskDone()

    OUT = sheet
