/**
 * App.jsx — Admin dashboard showing sandbox usage stats.
 *
 * Polls /admin/stats, /admin/usage, and /operator/list every 10 seconds.
 * Shows: total calls, error rate, developer signups, per-endpoint breakdown,
 * and registered operators.
 */
import React, { useState, useEffect } from "react";
import StatCard from "./components/StatCard";

const S = { maxWidth: "900px", margin: "0 auto", padding: "2rem 1rem", fontFamily: "-apple-system, sans-serif" };
const grid = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 24 };
const card = { background: "#fff", border: "1px solid #dee2e6", borderRadius: 8, padding: "1rem" };
const tbl = { width: "100%", borderCollapse: "collapse", fontSize: 14 };
const th = { textAlign: "left", padding: "8px 12px", borderBottom: "1px solid #dee2e6", color: "#666", fontSize: 12, textTransform: "uppercase" };
const td = { padding: "8px 12px", borderBottom: "1px solid #f0f0f0" };

export default function App() {
  const [stats, setStats] = useState(null);
  const [usage, setUsage] = useState(null);
  const [operators, setOperators] = useState([]);
  const [error, setError] = useState("");

  async function refresh() {
    try {
      const [s, u, o] = await Promise.all([
        fetch("/admin/stats").then(r => r.json()),
        fetch("/admin/usage").then(r => r.json()),
        fetch("/operator/list").then(r => r.json()),
      ]);
      setStats(s);
      setUsage(u);
      setOperators(o);
      setError("");
    } catch {
      setError("Cannot reach API. Is the server running?");
    }
  }

  useEffect(() => { refresh(); const t = setInterval(refresh, 10000); return () => clearInterval(t); }, []);

  return (
    <div style={S}>
      <h1 style={{ marginBottom: 4 }}>Admin Dashboard</h1>
      <p style={{ color: "#666", marginBottom: 24 }}>CAMARA Canada Sandbox — real-time usage and operator status</p>
      {error && <p style={{ color: "red" }}>{error}</p>}

      {stats && (
        <div style={grid}>
          <StatCard label="Total API Calls" value={stats.totalApiCalls} />
          <StatCard label="Error Rate" value={`${stats.errorRate}%`} />
          <StatCard label="Developer Signups" value={stats.developerSignups} />
          <StatCard label="Endpoints" value={stats.endpointsAvailable} />
        </div>
      )}

      {stats?.carriersActive && Object.keys(stats.carriersActive).length > 0 && (
        <div style={{ ...card, marginBottom: 24 }}>
          <h3 style={{ marginBottom: 8 }}>Calls by Carrier</h3>
          <table style={tbl}>
            <thead><tr><th style={th}>Carrier</th><th style={th}>Calls</th></tr></thead>
            <tbody>
              {Object.entries(stats.carriersActive).map(([k, v]) => (
                <tr key={k}><td style={td}>{k}</td><td style={td}>{v}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {usage?.endpoints && Object.keys(usage.endpoints).length > 0 && (
        <div style={{ ...card, marginBottom: 24 }}>
          <h3 style={{ marginBottom: 8 }}>Endpoint Usage</h3>
          <table style={tbl}>
            <thead><tr><th style={th}>Endpoint</th><th style={th}>Calls</th><th style={th}>Errors</th><th style={th}>Avg Latency</th></tr></thead>
            <tbody>
              {Object.entries(usage.endpoints).map(([ep, d]) => (
                <tr key={ep}><td style={td}><code>{ep}</code></td><td style={td}>{d.totalCalls}</td><td style={td}>{d.errors}</td><td style={td}>{d.avgLatencyMs}ms</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ ...card, marginBottom: 24 }}>
        <h3 style={{ marginBottom: 8 }}>Registered Operators ({operators.length})</h3>
        {operators.length === 0 ? (
          <p style={{ color: "#999" }}>No operators registered yet. Operators can onboard at <code>localhost:3001</code>.</p>
        ) : (
          <table style={tbl}>
            <thead><tr><th style={th}>Organization</th><th style={th}>Carrier</th><th style={th}>Progress</th></tr></thead>
            <tbody>
              {operators.map(o => (
                <tr key={o.operatorId}><td style={td}>{o.organizationName}</td><td style={td}>{o.carrierName}</td><td style={td}>{o.completedSteps}/{o.totalSteps} steps</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <button onClick={refresh} style={{ padding: "0.5rem 1rem", background: "#0f3460", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>
        Refresh Now
      </button>
    </div>
  );
}
