import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Download,
  FileText,
  Filter,
  FolderPlus,
  RefreshCcw,
  Search,
  ShieldCheck,
  Upload,
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // Keep default error message.
    }
    throw new Error(message);
  }
  return response.json();
}

function App() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [filters, setFilters] = useState({ keyword: "", sender: "", event_type: "" });
  const [form, setForm] = useState({ title: "", investigator: "", description: "" });
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    loadCases();
  }, []);

  useEffect(() => {
    if (selectedCase?.id) {
      loadCaseData(selectedCase.id);
    }
  }, [selectedCase?.id]);

  async function loadCases() {
    try {
      setError("");
      const data = await api("/cases");
      setCases(data);
      if (!selectedCase && data.length) {
        setSelectedCase(data[0]);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadCaseData(caseId, nextFilters = filters) {
    try {
      setError("");
      const params = new URLSearchParams();
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value) params.set(key, value);
      });
      const [evidenceData, timelineData] = await Promise.all([
        api(`/cases/${caseId}/evidence`),
        api(`/cases/${caseId}/timeline?${params.toString()}`),
      ]);
      setEvidence(evidenceData);
      setTimeline(timelineData);
    } catch (err) {
      setError(err.message);
    }
  }

  async function createCase(event) {
    event.preventDefault();
    if (!form.title.trim()) return;
    try {
      setStatus("Creating case...");
      setError("");
      const created = await api("/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      setForm({ title: "", investigator: "", description: "" });
      setSelectedCase(created);
      await loadCases();
      setStatus("Case created.");
    } catch (err) {
      setError(err.message);
    } finally {
      setTimeout(() => setStatus(""), 2400);
    }
  }

  async function uploadEvidence(event) {
    const file = event.target.files?.[0];
    if (!file || !selectedCase) return;
    try {
      setStatus("Uploading and parsing evidence...");
      setError("");
      const formData = new FormData();
      formData.append("file", file);
      await fetch(`${API_BASE}/cases/${selectedCase.id}/evidence`, {
        method: "POST",
        body: formData,
      }).then(async (response) => {
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.detail || "Upload failed");
        }
      });
      await loadCaseData(selectedCase.id);
      setStatus("Evidence parsed.");
    } catch (err) {
      setError(err.message);
    } finally {
      event.target.value = "";
      setTimeout(() => setStatus(""), 2400);
    }
  }

  function updateFilters(next) {
    setFilters(next);
    if (selectedCase) {
      loadCaseData(selectedCase.id, next);
    }
  }

  const summary = useMemo(() => {
    const messages = evidence.reduce((sum, item) => sum + (item.statistics?.message_count || 0), 0);
    const participants = new Set();
    evidence.forEach((item) => {
      (item.statistics?.participants || []).forEach((name) => participants.add(name));
    });
    return { messages, participants: participants.size, evidence: evidence.length };
  }, [evidence]);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={28} />
          <div>
            <h1>ArtifactX</h1>
            <p>WhatsApp forensic workspace</p>
          </div>
        </div>

        <form className="case-form" onSubmit={createCase}>
          <label>
            Case title
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </label>
          <label>
            Investigator
            <input value={form.investigator} onChange={(e) => setForm({ ...form, investigator: e.target.value })} />
          </label>
          <label>
            Description
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </label>
          <button type="submit" className="primary">
            <FolderPlus size={18} />
            Create
          </button>
        </form>

        <div className="case-list">
          <div className="panel-title">
            <span>Cases</span>
            <button title="Refresh cases" className="icon-button" onClick={loadCases}>
              <RefreshCcw size={16} />
            </button>
          </div>
          {cases.map((item) => (
            <button
              key={item.id}
              className={`case-row ${selectedCase?.id === item.id ? "active" : ""}`}
              onClick={() => setSelectedCase(item)}
            >
              <span>{item.title}</span>
              <small>{item.investigator}</small>
            </button>
          ))}
        </div>
      </aside>

      <section className="workspace">
        {error && <div className="toast error">{error}</div>}
        {status && <div className="toast">{status}</div>}

        {selectedCase ? (
          <>
            <header className="case-header">
              <div>
                <p className="eyebrow">Active case</p>
                <h2>{selectedCase.title}</h2>
                <p>{selectedCase.description || "No description provided."}</p>
              </div>
              <div className="actions">
                <label className="upload-button">
                  <Upload size={18} />
                  Upload .txt
                  <input type="file" accept=".txt,text/plain" onChange={uploadEvidence} />
                </label>
                <a className="secondary" href={`${API_BASE}/cases/${selectedCase.id}/report`}>
                  <Download size={18} />
                  Report
                </a>
              </div>
            </header>

            <section className="metrics">
              <Metric label="Evidence files" value={summary.evidence} />
              <Metric label="Messages" value={summary.messages} />
              <Metric label="Participants" value={summary.participants} />
            </section>

            <section className="split">
              <div className="panel">
                <div className="panel-title">
                  <span>Evidence</span>
                  <FileText size={18} />
                </div>
                {evidence.length ? (
                  evidence.map((item) => <EvidenceItem key={item.id} item={item} />)
                ) : (
                  <p className="empty">Upload a WhatsApp .txt export to begin analysis.</p>
                )}
              </div>

              <div className="panel timeline-panel">
                <div className="panel-title">
                  <span>Timeline</span>
                  <Filter size={18} />
                </div>
                <div className="filters">
                  <label>
                    <Search size={15} />
                    <input
                      placeholder="Keyword"
                      value={filters.keyword}
                      onChange={(e) => updateFilters({ ...filters, keyword: e.target.value })}
                    />
                  </label>
                  <input
                    placeholder="Sender"
                    value={filters.sender}
                    onChange={(e) => updateFilters({ ...filters, sender: e.target.value })}
                  />
                  <select
                    value={filters.event_type}
                    onChange={(e) => updateFilters({ ...filters, event_type: e.target.value })}
                  >
                    <option value="">All types</option>
                    <option value="message">Message</option>
                    <option value="media">Media</option>
                    <option value="deleted">Deleted</option>
                    <option value="system">System</option>
                  </select>
                </div>
                <TimelineTable events={timeline} />
              </div>
            </section>
          </>
        ) : (
          <div className="empty-state">
            <ShieldCheck size={42} />
            <h2>Create your first case</h2>
            <p>Use the case form to start an ArtifactX investigation workspace.</p>
          </div>
        )}
      </section>
    </main>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function EvidenceItem({ item }) {
  return (
    <article className="evidence-item">
      <div>
        <strong>{item.filename}</strong>
        <span>{item.parse_status}</span>
      </div>
      <p>SHA-256: {item.sha256}</p>
      <small>
        {item.size_bytes} bytes | {item.statistics?.message_count || 0} messages
      </small>
    </article>
  );
}

function TimelineTable({ events }) {
  if (!events.length) {
    return <p className="empty">No timeline events match the current filters.</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Actor</th>
            <th>Type</th>
            <th>Summary</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td>{event.timestamp ? new Date(event.timestamp).toLocaleString() : "Unknown"}</td>
              <td>{event.actor || "System"}</td>
              <td>
                <span className={`badge ${event.event_type}`}>{event.event_type}</span>
              </td>
              <td>{event.summary}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
