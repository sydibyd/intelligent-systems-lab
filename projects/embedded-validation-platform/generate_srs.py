from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from pathlib import Path

OUTPUT = Path("requirements/EVAP_Software_Requirements_SRS_v1.xlsx")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

wb = Workbook()
ws = wb.active
ws.title = "Requirements_SRS"

headers = [
    "Requirement_ID",
    "Subsystem",
    "Description",
    "Preconditions",
    "Inputs",
    "Expected_Behavior",
    "Acceptance_Criteria",
    "ASIL",
    "Priority",
    "Verification_Method",
    "Test_ID",
    "Status",
    "Version",
]

requirements = [
    ("SW-001", "BMS", "Detect cell overvoltage",
     "BMS initialized", "Cell voltage > configured threshold",
     "Overvoltage fault activated", "Detection <= 100 ms",
     "TBD", "High", "HIL", "TC-001", "Approved", "1.0"),

    ("SW-002", "BMS", "Detect cell undervoltage",
     "BMS initialized", "Cell voltage < configured threshold",
     "Undervoltage fault activated", "Detection <= 150 ms",
     "TBD", "High", "HIL", "TC-002", "Approved", "1.0"),

    ("SW-003", "Thermal", "Monitor battery temperature",
     "Temperature sensors operational", "Temperature > configured limit",
     "Thermal protection activated", "Fault flag activated",
     "TBD", "High", "HIL", "TC-003", "Approved", "1.0"),

    ("SW-004", "CAN", "Detect CAN communication timeout",
     "CAN communication established", "No CAN message received",
     "Communication fault activated", "Timeout <= 500 ms",
     "TBD", "High", "SIL", "TC-004", "Approved", "1.0"),

    ("SW-005", "Diagnostics", "Support UDS diagnostic session",
     "ECU powered", "UDS session request",
     "Valid diagnostic response", "Positive response when permitted",
     "TBD", "Medium", "HIL", "TC-005", "Approved", "1.0"),

    ("SW-006", "Watchdog", "Detect software watchdog timeout",
     "Watchdog enabled", "Software task stops responding",
     "Watchdog recovery triggered", "Recovery within configured timeout",
     "TBD", "High", "HIL", "TC-006", "Approved", "1.0"),

    ("SW-007", "Power", "Detect low supply voltage",
     "ECU running", "Supply voltage below threshold",
     "Low-voltage fault activated", "Fault detected",
     "TBD", "High", "HIL", "TC-007", "Approved", "1.0"),

    ("SW-008", "Control", "Validate startup initialization",
     "ECU powered off", "Power-on event",
     "System enters operational state", "Initialization successful",
     "TBD", "High", "SIL", "TC-008", "Approved", "1.0"),

    ("SW-009", "CAN", "Validate CAN message transmission",
     "CAN network active", "Transmission trigger",
     "CAN frame transmitted", "Correct identifier and payload",
     "TBD", "Medium", "SIL", "TC-009", "Approved", "1.0"),

    ("SW-010", "Diagnostics", "Store diagnostic trouble codes",
     "Fault detection enabled", "Diagnostic fault injected",
     "DTC stored", "DTC readable through diagnostics",
     "TBD", "Medium", "HIL", "TC-010", "Approved", "1.0"),

    ("SW-011", "BMS", "Validate state-of-charge calculation",
     "Current sensor operational", "Current measurement",
     "SOC updated", "SOC error within configured tolerance",
     "TBD", "Medium", "SIL", "TC-011", "Approved", "1.0"),

    ("SW-012", "Safety", "Enter safe state after critical fault",
     "System operational", "Critical fault injected",
     "System transitions to safe state", "Safe state reached within specified time",
     "TBD", "High", "HIL", "TC-012", "Approved", "1.0"),
]

ws.append(headers)
for row in requirements:
    ws.append(row)

tc = wb.create_sheet("Test_Cases")
tc.append([
    "Test_ID", "Requirement_ID", "Test_Name",
    "Environment", "Expected_Result", "Status"
])

for req in requirements:
    tc.append([
        req[10],
        req[0],
        "Verify " + req[2],
        req[9],
        req[5],
        "Not Executed",
    ])

trace = wb.create_sheet("Traceability")
trace.append(["Requirement_ID", "Test_ID", "Coverage_Status"])
for req in requirements:
    trace.append([req[0], req[10], "Mapped"])

params = wb.create_sheet("Parameters")
params.append(["Parameter", "Value", "Unit", "Description"])
params.append(["OV_DETECTION_TIME", 100, "ms", "Example overvoltage detection time"])
params.append(["UV_DETECTION_TIME", 150, "ms", "Example undervoltage detection time"])
params.append(["CAN_TIMEOUT", 500, "ms", "Example CAN timeout"])

pipeline = wb.create_sheet("Pipeline_Config")
pipeline.append(["Parameter", "Value"])
pipeline.append(["CI_Engine", "Jenkins"])
pipeline.append(["Test_Framework", "pytest"])
pipeline.append(["Container_Platform", "Docker"])
pipeline.append(["Default_Environment", "SIL"])

readme = wb.create_sheet("README")
readme.append(["EVAP Software Requirements Specification"])
readme.append(["Version", "1.0"])
readme.append(["Purpose", "Example requirements for EVAP development"])
readme.append(["Important", "All requirements and thresholds are fictional."])
readme.append(["ASIL", "TBD: requires an approved safety assessment."])

for sheet in wb.worksheets:
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions

    for cell in sheet[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = PatternFill("solid", fgColor="17365D")
        cell.alignment = Alignment(wrap_text=True)

    for column in sheet.columns:
        letter = get_column_letter(column[0].column)
        max_length = max(
            len(str(cell.value or "")) for cell in column
        )
        sheet.column_dimensions[letter].width = min(max_length + 3, 55)

wb.save(OUTPUT)

print(f"Excel generated: {OUTPUT}")
print(f"Requirements: {len(requirements)}")
print(f"Sheets: {wb.sheetnames}")
