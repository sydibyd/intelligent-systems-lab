from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openpyxl import load_workbook
from io import BytesIO

app = FastAPI(title="EVAP API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

requirements = []

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

@app.get("/api/requirements")
def get_requirements():
    return requirements

@app.get("/api/dashboard")
def dashboard():
    return {
        "requirements": len(requirements),
        "test_cases": 0,
        "executed_tests": 0,
        "pass_rate": None,
    }

@app.post("/api/requirements/import")
async def import_excel(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(400, "Only .xlsx files are supported")

    content = await file.read()
    if len(content) > 5_000_000:
        raise HTTPException(413, "File exceeds 5 MB")

    try:
        wb = load_workbook(BytesIO(content), read_only=True, data_only=True)
        ws = wb["Requirements_SRS"] if "Requirements_SRS" in wb.sheetnames else wb.active
        rows = ws.iter_rows(values_only=True)
        headers = [str(v).strip() if v is not None else "" for v in next(rows)]

        if len(headers) != len(set(headers)) or not any(headers):
            raise ValueError("Invalid or duplicate column headers")

        data = [
            dict(zip(headers, [str(v) if v is not None else "" for v in row]))
            for row in rows
            if any(v is not None for v in row)
        ]
        wb.close()
    except Exception as exc:
        raise HTTPException(400, f"Invalid Excel file: {exc}")

    requirements.clear()
    requirements.extend(data)

    return {"imported": len(data), "columns": headers}
