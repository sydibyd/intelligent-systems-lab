import io, os, json
from contextlib import contextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile, File, HTTPException
from openpyxl import load_workbook
import psycopg
from psycopg.rows import dict_row

from execution_api import router, initialize_execution_database

from campaign_api import router as campaign_router, initialize_campaign_database, recover_interrupted_campaigns

app = FastAPI(title='EVAP API', version='0.3.0')
app.include_router(router)
app.include_router(campaign_router)
DB = os.getenv('DATABASE_URL', 'postgresql://evap:evap_dev@db:5432/evap')

@contextmanager
def conn():
    with psycopg.connect(DB, row_factory=dict_row) as c:
        yield c

@app.on_event('startup')
def init():
    initialize_execution_database()
    initialize_campaign_database()
    recovered = recover_interrupted_campaigns()
    if recovered:
        print(f"EVAP recovery: {recovered} interrupted campaign(s)")
    with conn() as c:
        c.execute('CREATE TABLE IF NOT EXISTS requirements (id TEXT PRIMARY KEY, subsystem TEXT, description TEXT, priority TEXT, status TEXT, payload JSONB NOT NULL, updated_at TIMESTAMPTZ DEFAULT now())')
        c.execute('CREATE TABLE IF NOT EXISTS test_cases (id TEXT PRIMARY KEY, requirement_id TEXT REFERENCES requirements(id), name TEXT, environment TEXT, status TEXT, payload JSONB NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS imports (id BIGSERIAL PRIMARY KEY, filename TEXT, requirements_count INTEGER, tests_count INTEGER, imported_at TIMESTAMPTZ DEFAULT now())')

@app.get('/api/health')
def health():
    with conn() as c: c.execute('SELECT 1')
    return {'status':'ok','version':'0.3.0','database':'connected'}

@app.get('/api/requirements')
def requirements():
    with conn() as c:
        return [r['payload'] for r in c.execute('SELECT payload FROM requirements ORDER BY id').fetchall()]

@app.get('/api/test-cases')
def tests():
    with conn() as c:
        return [r['payload'] for r in c.execute('SELECT payload FROM test_cases ORDER BY id').fetchall()]

@app.get('/api/imports')
def imports():
    with conn() as c:
        return c.execute('SELECT id, filename, requirements_count, tests_count, imported_at FROM imports ORDER BY id DESC LIMIT 20').fetchall()

@app.get('/api/dashboard')
def dashboard():
    with conn() as c:
        nr=c.execute('SELECT count(*) AS n FROM requirements').fetchone()['n']
        nt=c.execute('SELECT count(*) AS n FROM test_cases').fetchone()['n']
        mapped=c.execute('SELECT count(DISTINCT requirement_id) AS n FROM test_cases WHERE requirement_id IS NOT NULL').fetchone()['n']
        summary = c.execute('''
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE verdict = 'PASSED') AS passed,
                COUNT(*) FILTER (WHERE verdict = 'FAILED') AS failed,
                COUNT(*) FILTER (WHERE verdict = 'ERROR') AS errors,
                COUNT(DISTINCT test_id) AS distinct_tests
            FROM test_executions
        ''').fetchone()
    total = summary['total']
    return {
        'requirements': nr,
        'test_cases': nt,
        'mapped_requirements': mapped,
        'mapping_coverage': round(100*mapped/nr,1) if nr else None,
        'total_executions': total,
        'executed_tests': summary['distinct_tests'],
        'passed_executions': summary['passed'],
        'failed_executions': summary['failed'],
        'error_executions': summary['errors'],
        'pass_rate': round(100*summary['passed']/total,1) if total else None
    }

def sheet_rows(wb, name, required):
    if name not in wb.sheetnames: raise ValueError(f'Missing sheet: {name}')
    values=wb[name].iter_rows(values_only=True)
    headers=[str(v).strip() if v is not None else '' for v in next(values)]
    if len(headers)!=len(set(headers)) or not set(required).issubset(headers):
        raise ValueError(f'Invalid headers in {name}; required: {required}')
    return [{h: str(v).strip() if v is not None else '' for h,v in zip(headers,row)} for row in values if any(v is not None for v in row)]

@app.post('/api/requirements/import')
async def import_excel(file: UploadFile=File(...)):
    if not file.filename or not file.filename.lower().endswith('.xlsx'): raise HTTPException(400,'Only .xlsx supported')
    content=await file.read(5_000_001)
    if len(content)>5_000_000: raise HTTPException(413,'Maximum file size 5 MB')
    try:
        wb=load_workbook(io.BytesIO(content),read_only=True,data_only=True)
        reqs=sheet_rows(wb,'Requirements_SRS',['Requirement_ID','Description'])
        tests=sheet_rows(wb,'Test_Cases',['Test_ID','Requirement_ID']) if 'Test_Cases' in wb.sheetnames else []
        wb.close()
        ids=[r['Requirement_ID'] for r in reqs]
        tids=[t['Test_ID'] for t in tests]
        if not ids or any(not x for x in ids) or len(ids)!=len(set(ids)): raise ValueError('Missing or duplicate requirement IDs')
        if any(not x for x in tids) or len(tids)!=len(set(tids)): raise ValueError('Missing or duplicate test IDs')
        if any(t['Requirement_ID'] not in ids for t in tests): raise ValueError('Test references unknown requirement')
        if any(not r['Description'] for r in reqs): raise ValueError('Requirement description is missing')
    except Exception as e: raise HTTPException(400,str(e))
    with conn() as c:
        # Atomic replacement: preserve prior dataset if import fails.
        c.execute('DELETE FROM test_cases')
        c.execute('DELETE FROM requirements')
        for r in reqs:
            c.execute('INSERT INTO requirements(id,subsystem,description,priority,status,payload) VALUES (%s,%s,%s,%s,%s,%s::jsonb)',(r['Requirement_ID'],r.get('Subsystem',''),r['Description'],r.get('Priority',''),r.get('Status',''),json.dumps(r)))
        for t in tests:
            c.execute('INSERT INTO test_cases(id,requirement_id,name,environment,status,payload) VALUES (%s,%s,%s,%s,%s,%s::jsonb)',(t['Test_ID'],t['Requirement_ID'],t.get('Test_Name',''),t.get('Environment',''),t.get('Status',''),json.dumps(t)))
        c.execute('INSERT INTO imports(filename,requirements_count,tests_count) VALUES (%s,%s,%s)',(file.filename,len(reqs),len(tests)))
    return {'imported':len(reqs),'test_cases':len(tests)}
