/**
 * SnippetDisplay.jsx — Copy-paste SDK snippets for curl, Python, Node.js.
 *
 * Generates code snippets based on the last surface called and the
 * developer's API key. Allows one-click copy.
 */
import React, { useState } from "react";

const SURFACE_PATHS = {
  "SIM Swap — Retrieve Date": "/sim-swap/v1/retrieve-date",
  "SIM Swap — Check": "/sim-swap/v1/check",
  "Number Verification": "/number-verification/v1/verify",
  "Location Verification": "/location-verification/v1/verify",
  "Fraud Score (sandbox-only)": "/sandbox/fraud-score",
};

function curlSnippet(apiKey, path) {
  return `curl -X POST http://localhost:8080${path} \\
  -H "Authorization: Bearer ${apiKey}" \\
  -H "Content-Type: application/json" \\
  -d '{"phoneNumber": "+14165550100"}'`;
}

function pythonSnippet(apiKey, path) {
  return `import httpx

resp = httpx.post(
    "http://localhost:8080${path}",
    headers={"Authorization": "Bearer ${apiKey}"},
    json={"phoneNumber": "+14165550100"},
)
print(resp.json())`;
}

function nodeSnippet(apiKey, path) {
  return `const resp = await fetch("http://localhost:8080${path}", {
  method: "POST",
  headers: {
    Authorization: "Bearer ${apiKey}",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ phoneNumber: "+14165550100" }),
});
console.log(await resp.json());`;
}

export default function SnippetDisplay({ apiKey, lastResponse, surface }) {
  const [copied, setCopied] = useState("");
  const key = apiKey || "YOUR_API_KEY";
  const path = SURFACE_PATHS[surface] || "/sim-swap/v1/retrieve-date";

  function copy(text, label) {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(""), 2000);
  }

  const snippets = [
    { label: "curl", code: curlSnippet(key, path) },
    { label: "Python", code: pythonSnippet(key, path) },
    { label: "Node.js", code: nodeSnippet(key, path) },
  ];

  return (
    <section className="card">
      <h2>SDK Snippets</h2>
      <p>Copy-paste these into your app. Replace the phone number as needed.</p>

      {snippets.map(({ label, code }) => (
        <div key={label} className="snippet">
          <div className="snippet-header">
            <strong>{label}</strong>
            <button onClick={() => copy(code, label)}>
              {copied === label ? "Copied!" : "Copy"}
            </button>
          </div>
          <pre>{code}</pre>
        </div>
      ))}

      {lastResponse && (
        <div className="last-response">
          <h3>Last Response</h3>
          <pre>{JSON.stringify(lastResponse, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}
