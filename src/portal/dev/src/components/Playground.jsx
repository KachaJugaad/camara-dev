/**
 * Playground.jsx — Live API playground for testing CAMARA surfaces.
 *
 * Lets the developer select a surface, fill in parameters, and
 * make a real call to the sandbox. Shows formatted JSON response.
 */
import React, { useState } from "react";

const SURFACES = {
  "SIM Swap — Retrieve Date": {
    path: "/sim-swap/v1/retrieve-date",
    defaultBody: { phoneNumber: "+14165550100" },
  },
  "SIM Swap — Check": {
    path: "/sim-swap/v1/check",
    defaultBody: { phoneNumber: "+14165550100", maxAge: 24 },
  },
  "Number Verification": {
    path: "/number-verification/v1/verify",
    defaultBody: { phoneNumber: "+14165550100" },
  },
  "Location Verification": {
    path: "/location-verification/v1/verify",
    defaultBody: {
      device: { phoneNumber: "+14165550100" },
      area: {
        areaType: "CIRCLE",
        center: { latitude: 43.6532, longitude: -79.3832 },
        radius: 10000,
      },
    },
  },
  "Fraud Score (sandbox-only)": {
    path: "/sandbox/fraud-score",
    defaultBody: {
      phoneNumber: "+14165550100",
      location: { latitude: 43.6532, longitude: -79.3832, radiusMeters: 5000 },
    },
  },
};

export default function Playground({ apiKey, onResponse }) {
  const [surface, setSurface] = useState(Object.keys(SURFACES)[0]);
  const [body, setBody] = useState(
    JSON.stringify(SURFACES[Object.keys(SURFACES)[0]].defaultBody, null, 2)
  );
  const [response, setResponse] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [latency, setLatency] = useState(null);

  function handleSurfaceChange(name) {
    setSurface(name);
    setBody(JSON.stringify(SURFACES[name].defaultBody, null, 2));
    setResponse(null);
    setStatus(null);
  }

  async function handleCall() {
    if (!apiKey) {
      setResponse({ error: "Get an API key first (tab 1)" });
      setStatus(400);
      return;
    }
    setLoading(true);
    const start = performance.now();
    try {
      const resp = await fetch(SURFACES[surface].path, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: body,
      });
      const data = await resp.json();
      setLatency(Math.round(performance.now() - start));
      setResponse(data);
      setStatus(resp.status);
      onResponse(data, surface);
    } catch (err) {
      setLatency(null);
      setResponse({ error: "Cannot reach API. Is the server running?" });
      setStatus(0);
    } finally {
      setLoading(false);
    }
  }

  const isError = status && status >= 400;

  return (
    <section className="card">
      <h2>API Playground</h2>

      {!apiKey && (
        <p className="warning">No API key set. Go to "Get Started" tab first.</p>
      )}

      <label>
        CAMARA Surface
        <select value={surface} onChange={(e) => handleSurfaceChange(e.target.value)}>
          {Object.keys(SURFACES).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </label>

      <label>
        Request Body (JSON)
        <textarea
          rows={8}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          spellCheck={false}
        />
      </label>

      <button onClick={handleCall} disabled={loading}>
        {loading ? "Calling..." : "Try it"}
      </button>

      {response && (
        <div className={`response ${isError ? "error-response" : "success-response"}`}>
          <div className="response-meta">
            <span>Status: {status}</span>
            {latency && <span>Latency: {latency}ms</span>}
          </div>
          <pre>{JSON.stringify(response, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}
