import React, { useEffect, useState } from 'react';

const SIL_IDS = ['TC-004', 'TC-008', 'TC-009', 'TC-011'];

export default function TestCampaigns({ tests, onCompleted }) {
  const [name, setName] = useState('BMS SIL Regression Campaign');
  const [selected, setSelected] = useState(SIL_IDS);
  const [campaigns, setCampaigns] = useState([]);
  const [details, setDetails] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');

  const available = tests.filter(
    t => SIL_IDS.includes(t.Test_ID) &&
      t.Environment?.toUpperCase() === 'SIL'
  );

  const loadCampaigns = async () => {
    const response = await fetch('/api/campaigns');
    if (!response.ok) throw new Error(await response.text());
    setCampaigns(await response.json());
  };

  useEffect(() => {
    loadCampaigns().catch(e => setError(e.message));
  }, []);

  const toggle = id => {
    setSelected(current =>
      current.includes(id)
        ? current.filter(x => x !== id)
        : [...current, id]
    );
  };

  const viewResults = async id => {
    try {
      setError('');
      const response = await fetch(`/api/campaigns/${id}`);
      if (!response.ok) throw new Error(await response.text());
      setDetails(await response.json());
    } catch (e) {
      setError(e.message);
    }
  };

  const runCampaign = async () => {
    if (!name.trim() || !selected.length) return;

    setRunning(true);
    setError('');

    try {
      const response = await fetch('/api/campaigns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          test_ids: selected
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : JSON.stringify(data.detail)
        );
      }

      await loadCampaigns();
      await viewResults(data.campaign_id);
      if (onCompleted) await onCompleted();
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <>
      <section className="panel">
        <h2>Create SIL Test Campaign</h2>
        <p>Execute registered SIL demonstration tests.</p>

        <div className="campaign-form">
          <label htmlFor="campaign-name">Campaign Name</label>
          <input
            id="campaign-name"
            value={name}
            maxLength={120}
            disabled={running}
            onChange={e => setName(e.target.value)}
          />

          <h3>Available SIL Tests</h3>

          <div className="campaign-test-list">
            {available.map(t => (
              <label className="campaign-test" key={t.Test_ID}>
                <input
                  type="checkbox"
                  checked={selected.includes(t.Test_ID)}
                  disabled={running}
                  onChange={() => toggle(t.Test_ID)}
                />
                <span>
                  <strong>{t.Test_ID}</strong> — {t.Test_Name}
                </span>
              </label>
            ))}
          </div>

          <button
            className="primary-button"
            disabled={running || !selected.length || !name.trim()}
            onClick={runCampaign}
          >
            {running ? 'Running Campaign...' : '▶ Run Campaign'}
          </button>

          {error && <p role="alert">{error}</p>}
        </div>
      </section>

      <section className="panel">
        <h2>Campaign History</h2>

        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                {['ID', 'Name', 'Tests', 'Passed', 'Failed',
                  'Errors', 'Status', 'Details'].map(x => (
                  <th key={x}>{x}</th>
                ))}
              </tr>
            </thead>

            <tbody>
              {campaigns.map(c => (
                <tr key={c.id}>
                  <td>#{c.id}</td>
                  <td>{c.name}</td>
                  <td>{c.total_tests}</td>
                  <td>{c.passed}</td>
                  <td>{c.failed}</td>
                  <td>{c.errors}</td>
                  <td>{c.status}</td>
                  <td>
                    <button onClick={() => viewResults(c.id)}>
                      View Results
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {details && (
        <section className="panel">
          <h2>Campaign #{details.id} — {details.name}</h2>

          <div className="campaign-summary">
            <span>Status: <b>{details.status}</b></span>
            <span>Total: <b>{details.total_tests}</b></span>
            <span>Passed: <b>{details.passed}</b></span>
            <span>Failed: <b>{details.failed}</b></span>
            <span>Errors: <b>{details.errors}</b></span>
          </div>

          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  {['Execution', 'Test', 'Requirement',
                    'Verdict', 'Duration', 'Logs'].map(x => (
                    <th key={x}>{x}</th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {(details.executions || []).map(e => (
                  <tr key={e.id}>
                    <td>#{e.id}</td>
                    <td>{e.test_id}</td>
                    <td>{e.requirement_id}</td>
                    <td>{e.verdict}</td>
                    <td>{e.duration_seconds}s</td>
                    <td>
                      <details>
                        <summary>View Logs</summary>
                        <pre className="campaign-logs">{e.logs}</pre>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
