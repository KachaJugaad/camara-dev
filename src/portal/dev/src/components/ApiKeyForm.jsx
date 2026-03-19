/**
 * ApiKeyForm.jsx — Get a sandbox API key instantly.
 *
 * Calls POST /sandbox/keys with email and optional carrier.
 * On success, passes the key to the parent via onKeyIssued callback.
 */
import React, { useState } from "react";

const CARRIERS = ["auto", "rogers", "bell", "telus"];

export default function ApiKeyForm({ apiKey, onKeyIssued }) {
  const [email, setEmail] = useState("");
  const [carrier, setCarrier] = useState("auto");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const body = { email };
      if (carrier !== "auto") body.carrier = carrier;
      const resp = await fetch("/sandbox/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setError(data.message || data.detail || "Request failed");
        return;
      }
      onKeyIssued(data.apiKey);
    } catch (err) {
      setError("Cannot reach sandbox API. Is the server running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <h2>Get Your API Key</h2>
      <p>Enter your email to get an instant sandbox key. No approval needed.</p>

      {apiKey && (
        <div className="key-display">
          <strong>Your key:</strong> <code>{apiKey}</code>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@startup.ca"
            required
          />
        </label>

        <label>
          Carrier (optional)
          <select value={carrier} onChange={(e) => setCarrier(e.target.value)}>
            {CARRIERS.map((c) => (
              <option key={c} value={c}>
                {c === "auto" ? "Auto-detect from phone number" : c.charAt(0).toUpperCase() + c.slice(1)}
              </option>
            ))}
          </select>
        </label>

        <button type="submit" disabled={loading}>
          {loading ? "Issuing..." : "Get API Key"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      <details>
        <summary>Or use a demo key</summary>
        <ul>
          <li><code>demo-sandbox-key-rogers</code> — Rogers</li>
          <li><code>demo-sandbox-key-bell</code> — Bell</li>
          <li><code>demo-sandbox-key-telus</code> — Telus</li>
          <li><code>demo-sandbox-key-auto</code> — Auto-detect</li>
        </ul>
        <button onClick={() => onKeyIssued("demo-sandbox-key-auto")}>
          Use demo key (auto)
        </button>
      </details>
    </section>
  );
}
