import React, {useEffect, useState} from "react";
import {createRoot} from "react-dom/client";
import "./style.css";

function App() {
  const [stats, setStats] = useState({});
  const [requirements, setRequirements] = useState([]);
  const [message, setMessage] = useState("");

  const refresh = async () => {
    const [s, r] = await Promise.all([
      fetch("/api/dashboard").then(r => r.json()),
      fetch("/api/requirements").then(r => r.json())
    ]);
    setStats(s);
    setRequirements(r);
  };

  useEffect(() => { refresh().catch(console.error); }, []);

  const upload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const form = new FormData();
    form.append("file", file);

    try {
      const response = await fetch("/api/requirements/import", {
        method: "POST",
        body: form
      });
      const result = await response.json();
      if (!response.ok) throw Error(result.detail);
      setMessage(`${result.imported} requirements imported`);
      await refresh();
    } catch (error) {
      setMessage(`Import error: ${error.message}`);
    }
  };

  return (
    <div className="layout">
      <aside>
        <h2>EVAP</h2>
        <p>VALIDATION PLATFORM</p>
        <nav>
          <div>◈ Dashboard</div>
          <div>▤ Requirements</div>
          <div>⚙ Test Management</div>
          <div>◇ CI/CD Pipelines</div>
          <div>▥ Reports</div>
        </nav>
        <footer>EVAP v0.1</footer>
      </aside>

      <main>
        <header>
          <div>
            <h1>Validation Dashboard</h1>
            <p>Embedded Software Validation Platform</p>
          </div>
          <span className="badge">● Development</span>
        </header>

        <section className="cards">
          <article><span>Requirements</span><strong>{stats.requirements ?? 0}</strong></article>
          <article><span>Test Cases</span><strong>{stats.test_cases ?? 0}</strong></article>
          <article><span>Executed Tests</span><strong>{stats.executed_tests ?? 0}</strong></article>
          <article><span>Pass Rate</span><strong>{stats.pass_rate == null ? "N/A" : `${stats.pass_rate}%`}</strong></article>
        </section>

        <section className="panel">
          <h2>Software Requirements Import</h2>
          <p>Import your Software Requirements Specification (SRS).</p>
          <label className="upload">
            Select Excel SRS (.xlsx)
            <input type="file" accept=".xlsx" onChange={upload}/>
          </label>
          <p>{message}</p>
        </section>

        <section className="panel">
          <h2>Requirements Explorer</h2>
          <p>{requirements.length} requirements loaded</p>
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  {Object.keys(requirements[0] || {}).map(k => <th key={k}>{k}</th>)}
                </tr>
              </thead>
              <tbody>
                {requirements.map((r, i) =>
                  <tr key={i}>
                    {Object.values(r).map((v, j) => <td key={j}>{v}</td>)}
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App/>);
