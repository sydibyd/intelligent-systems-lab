import React,{useState,useEffect} from 'react';
import {apiFetch} from './api.js';

async function request(path,method='GET',body){
 const r=await apiFetch(path,{method,...(body?{headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{})});
 if(!r.ok) throw Error('Request failed: HTTP '+r.status);
 return r.json();
}

export function ExecutionQueue({tests}){
 const [rows,setRows]=useState([]),[test,setTest]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const refresh=()=>request('/api/jobs').then(setRows).catch(e=>setError(e.message));
 useEffect(()=>{refresh();const timer=setInterval(refresh,5000);return()=>clearInterval(timer)},[]);
 async function submit(e){
  e.preventDefault();setBusy(true);setError('');
  try{await request('/api/jobs','POST',{test_id:test,idempotency_key:crypto.randomUUID()});await refresh()}catch(e){setError(e.message)}finally{setBusy(false)}
 }
 return <section className="panel"><h2>Distributed SIL execution</h2><p>HIL execution is disabled pending hardware qualification.</p>
 <form onSubmit={submit}><select required value={test} onChange={e=>setTest(e.target.value)}><option value="">Select test</option>{tests.filter(t=>['TC-004','TC-008','TC-009','TC-011'].includes(t.Test_ID)&&t.Environment?.toUpperCase()==='SIL').map(t=><option key={t.Test_ID}>{t.Test_ID}</option>)}</select><button disabled={busy||!test}>Submit job</button></form>
 <p role="status">{error}</p><div className="tablewrap"><table><thead><tr>{['Job','Test','Status','Worker','Execution','Created'].map(x=><th key={x}>{x}</th>)}</tr></thead><tbody>{rows.map(j=><tr key={j.id}><td>{j.id}</td><td>{j.test_id}</td><td>{j.status}</td><td>{j.worker_id||'—'}</td><td>{j.execution_id||'—'}</td><td>{new Date(j.created_at).toLocaleString()}</td></tr>)}</tbody></table></div></section>
}

export function AIStudio({requirements}){
 const [rows,setRows]=useState([]),[req,setReq]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[reason,setReason]=useState('');
 const refresh=()=>request('/api/ai-drafts').then(setRows).catch(e=>setError(e.message));
 useEffect(()=>{refresh()},[]);
 async function action(path,method,body){setBusy(true);setError('');try{await request(path,method,body);await refresh()}catch(e){setError(e.message)}finally{setBusy(false)}}
 return <section className="panel"><h2>AI Test Studio</h2><p>Generation sends the selected requirement to the configured external AI provider. Submit only authorized data. Drafts are never executable.</p>
 <form onSubmit={e=>{e.preventDefault();action('/api/ai-drafts','POST',{requirement_id:req})}}><select required value={req} onChange={e=>setReq(e.target.value)}><option value="">Select requirement</option>{requirements.map(r=><option key={r.Requirement_ID}>{r.Requirement_ID}</option>)}</select><button disabled={busy||!req}>Generate draft</button></form>
 <p role="status">{error}</p><label>Review reason <input value={reason} onChange={e=>setReason(e.target.value)} maxLength={2000}/></label>
 {rows.map(r=><article className="details" key={r.id}><h3>#{r.id} · {r.proposal.draft.title}</h3><p>{r.requirement_id} · {r.status} · {r.proposal.model}</p><p>Requested by: {r.requested_by} · Reviewed by: {r.reviewed_by||'—'}</p><p>Structural evaluation: {r.proposal.evaluation.structurally_valid?'Valid':'Invalid'}</p><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(r.proposal.draft,null,2)}</pre>{r.status==='PENDING_REVIEW'&&['APPROVED','REJECTED'].map(decision=><button key={decision} disabled={busy||reason.trim().length<10} onClick={()=>action('/api/ai-drafts/'+r.id,'PATCH',{decision,reason})}>{decision}</button>)}</article>)}</section>
}
