import React,{useEffect,useMemo,useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';
function App(){
 const [page,setPage]=useState('Dashboard'),[stats,setStats]=useState({}),[reqs,setReqs]=useState([]),[tests,setTests]=useState([]),[imports,setImports]=useState([]),[q,setQ]=useState(''),[sub,setSub]=useState('All'),[selected,setSelected]=useState(null),[msg,setMsg]=useState(''),[busy,setBusy]=useState(false);
 const get=async path=>{const r=await fetch('/api/'+path);if(!r.ok)throw Error(await r.text());return r.json()};
 const refresh=async()=>{const [s,r,t,i]=await Promise.all(['dashboard','requirements','test-cases','imports'].map(get));setStats(s);setReqs(r);setTests(t);setImports(i);
 const h=await get('executions');
 setHistory(h);
 };
 useEffect(()=>{refresh().catch(e=>setMsg(e.message))},[]);
 const upload=async e=>{const file=e.target.files[0];if(!file)return;setBusy(true);setMsg('');try{const body=new FormData();body.append('file',file);const r=await fetch('/api/requirements/import',{method:'POST',body});const d=await r.json();if(!r.ok)throw Error(d.detail);await refresh();setMsg(`${d.imported} requirements and ${d.test_cases} test cases imported`)}catch(e){setMsg('Import error: '+e.message)}finally{setBusy(false);e.target.value=''}};
 const [history,setHistory]=useState([]);
 const [running,setRunning]=useState(false);
 const [execution,setExecution]=useState(null);

 const runTest=async(testId)=>{
   setRunning(true);
   setMsg('');
   try {
     const response=await fetch(
       '/api/executions/'+encodeURIComponent(testId),
       {method:'POST'}
     );
     const data=await response.json();

     if(!response.ok)
       throw Error(data.detail || 'Execution failed');

     setExecution(data);
     setMsg('Execution completed: '+data.verdict);
     await refresh();
   } catch(error) {
     setMsg('Execution error: '+error.message);
   } finally {
     setRunning(false);
   }
 };

 const subs=['All',...new Set(reqs.map(r=>r.Subsystem).filter(Boolean))];
 const filtered=useMemo(()=>reqs.filter(r=>(sub==='All'||r.Subsystem===sub)&&Object.values(r).join(' ').toLowerCase().includes(q.toLowerCase())),[reqs,q,sub]);
 const menu=['Dashboard','Requirements','Test Cases','Test Executions','Traceability','Import History'];
 return <div className="layout"><aside><h2>EVAP</h2><small>VALIDATION PLATFORM</small><nav>{menu.map(m=><button className={page===m?'active':''} key={m} onClick={()=>setPage(m)}>{m}</button>)}</nav><footer>EVAP v0.3.1 · Development</footer></aside><main><header><div><h1>{page}</h1><p>A Universal CI/CD Validation Platform for Embedded Software Systems</p></div><span className="badge">● Development</span></header>
 {page==='Dashboard'&&<><div className="cards">{[['Requirements',stats.requirements??0],['Test Cases',stats.test_cases??0],['Mapped Requirements',stats.mapped_requirements??0],['Mapping Coverage',stats.mapping_coverage==null?'N/A':stats.mapping_coverage+'%'],
['Total Executions',stats.total_executions??0],
['Executed Test Cases',stats.executed_tests??0],
['Passed Executions',stats.passed_executions??0],
['Pass Rate',stats.pass_rate==null?'N/A':stats.pass_rate+'%']].map(([k,v])=><article key={k}><span>{k}</span><strong>{v}</strong></article>)}</div><section className="panel"><h2>Software Requirements Import</h2><p>Import an Excel workbook containing Requirements_SRS and optionally Test_Cases.</p><label className="upload">{busy?'Importing...':'Select Excel SRS (.xlsx)'}<input type="file" accept=".xlsx" disabled={busy} onChange={upload}/></label><p role="status">{msg}</p></section><section className="panel"><h2>Validation status</h2><p>SIL test execution is operational for registered demonstration tests. Mapping coverage and execution pass rate are different metrics.</p></section></>}
 {page==='Requirements'&&<section className="panel"><h2>Requirements Explorer</h2><div className="filters"><input placeholder="Search requirements..." value={q} onChange={e=>setQ(e.target.value)}/><select value={sub} onChange={e=>setSub(e.target.value)}>{subs.map(s=><option key={s}>{s}</option>)}</select></div><p>{filtered.length} / {reqs.length} requirements</p><div className="tablewrap"><table><thead><tr>{['ID','Subsystem','Description','Priority','Status','Test ID'].map(x=><th key={x}>{x}</th>)}</tr></thead><tbody>{filtered.map(r=><tr key={r.Requirement_ID} onClick={()=>setSelected(r)} className="clickable"><td>{r.Requirement_ID}</td><td>{r.Subsystem}</td><td>{r.Description}</td><td>{r.Priority}</td><td>{r.Status}</td><td>{r.Test_ID}</td></tr>)}</tbody></table></div>{selected&&<div className="details"><button onClick={()=>setSelected(null)}>Close details ×</button><h3>{selected.Requirement_ID} — {selected.Description}</h3>{Object.entries(selected).map(([k,v])=><p key={k}><b>{k}:</b> {v}</p>)}</div>}</section>}
 {page==='Test Cases'&&<section className="panel"><h2>Imported Test Cases</h2><div className="tablewrap"><table><thead><tr>{['Test ID','Requirement','Name','Environment','Status','Action'].map(x=><th key={x}>{x}</th>)}</tr></thead><tbody>{tests.map(t=><tr key={t.Test_ID}><td>{t.Test_ID}</td><td>{t.Requirement_ID}</td><td>{t.Test_Name}</td><td>{t.Environment}</td><td>{t.Status}</td><td>
 {t.Test_ID==='TC-004' && t.Environment?.toUpperCase()==='SIL'
 ? <button disabled={running} onClick={()=>runTest(t.Test_ID)}>
     {running?'Running...':'▶ Run Test'}
   </button>
 : 'Not available'}
 </td></tr>)}</tbody></table></div></section>}
 {page==='Test Executions'&&
 <section className="panel">
  <h2>SIL Test Execution</h2>
  <p>Execute registered simulation tests.</p>
  <button disabled={running} onClick={()=>runTest('TC-004')}>
   {running?'Running...':'▶ Run TC-004'}
  </button>
  <p role="status">{msg}</p>
  {execution&&
   <div className="details">
    <h3>Execution #{execution.execution_id}</h3>
    <p>Test: {execution.test_id}</p>
    <p>Verdict: <b>{execution.verdict}</b></p>
    <p>Duration: {execution.duration_seconds}s</p>
    <p>Simulation: Yes</p>
    <h3>pytest logs</h3>
    <pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>
     {execution.logs}
    </pre>
   </div>}
 </section>}
 {page==='Test Executions'&&
 <section className="panel">
  <h2>Execution History</h2>
  <p>{history.length} recent executions</p>
  <div className="tablewrap">
   <table>
    <thead>
     <tr>
      {['Execution','Test','Requirement','Environment','Verdict','Duration','Date','Logs'].map(x=><th key={x}>{x}</th>)}
     </tr>
    </thead>
    <tbody>
     {history.map(e=>
      <tr key={e.id}>
       <td>#{e.id}</td>
       <td>{e.test_id}</td>
       <td>{e.requirement_id}</td>
       <td>{e.environment}</td>
       <td>{e.verdict}</td>
       <td>{e.duration_seconds}s</td>
       <td>{new Date(e.executed_at).toLocaleString()}</td>
       <td>
        <button onClick={()=>setExecution({
         execution_id:e.id,
         test_id:e.test_id,
         verdict:e.verdict,
         duration_seconds:e.duration_seconds,
         logs:e.logs,
         simulation:true
        })}>
         View Logs
        </button>
       </td>
      </tr>
     )}
    </tbody>
   </table>
  </div>
 </section>}
 {page==='Traceability'&&<section className="panel"><h2>Requirement → Test Mapping</h2><p>Mapping is not evidence of successful execution.</p><div className="tablewrap"><table><thead><tr><th>Requirement</th><th>Associated Tests</th><th>Mapping</th></tr></thead><tbody>{reqs.map(r=>{const linked=tests.filter(t=>t.Requirement_ID===r.Requirement_ID);return <tr key={r.Requirement_ID}><td>{r.Requirement_ID}</td><td>{linked.map(t=>t.Test_ID).join(', ')||'—'}</td><td>{linked.length?'Mapped':'Unmapped'}</td></tr>})}</tbody></table></div></section>}
 {page==='Import History'&&<section className="panel"><h2>Import History</h2><div className="tablewrap"><table><thead><tr><th>Filename</th><th>Requirements</th><th>Test Cases</th><th>Date</th></tr></thead><tbody>{imports.map(i=><tr key={i.id}><td>{i.filename}</td><td>{i.requirements_count}</td><td>{i.tests_count}</td><td>{new Date(i.imported_at).toLocaleString()}</td></tr>)}</tbody></table></div></section>}
 </main></div>
}
createRoot(document.getElementById('root')).render(<App/>);
