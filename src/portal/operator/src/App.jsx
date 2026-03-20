/**
 * App.jsx — 8-step operator onboarding wizard.
 *
 * Flow: Register → MSISDN → Latency → Errors → Features → Endpoint → Test → Publish.
 * Each step posts to /operator/step/{id}/{step} and advances on success.
 */
import React, { useState } from "react";
import WizardStep from "./components/WizardStep";

const STEPS = [
  { num: 1, name: "Account Registration", fields: [
    { key: "organizationName", label: "Organization Name", placeholder: "Rogers Communications" },
    { key: "contactEmail", label: "Contact Email", placeholder: "engineer@rogers.com" },
    { key: "carrierName", label: "Carrier Name", placeholder: "rogers" },
  ]},
  { num: 2, name: "MSISDN Ranges", fields: [
    { key: "msisdnPrefixes", label: "MSISDN Prefixes (comma-separated)", placeholder: "1416, 1647, 1437" },
  ]},
  { num: 3, name: "Latency Profile", fields: [
    { key: "p50", label: "p50 Latency (ms)", placeholder: "120", type: "number" },
    { key: "p95", label: "p95 Latency (ms)", placeholder: "340", type: "number" },
    { key: "p99", label: "p99 Latency (ms)", placeholder: "890", type: "number" },
  ]},
  { num: 4, name: "Error Profile", fields: [
    { key: "timeoutProbability", label: "Timeout Rate (0-1)", placeholder: "0.045", type: "number" },
    { key: "unavailableProbability", label: "Unavailable Rate (0-1)", placeholder: "0.012", type: "number" },
  ]},
  { num: 5, name: "Feature Flags", fields: [
    { key: "simSwapSupported", label: "SIM Swap Supported", type: "checkbox" },
    { key: "numberVerifySupported", label: "Number Verification Supported", type: "checkbox" },
    { key: "locationSupported", label: "Location Verification Supported", type: "checkbox" },
  ]},
  { num: 6, name: "Endpoint Registration", fields: [
    { key: "endpointUrl", label: "Real CAMARA Endpoint URL (optional)", placeholder: "https://api.rogers.com/camara/v1" },
  ]},
  { num: 7, name: "Test Verification", fields: [] },
  { num: 8, name: "Publish", fields: [] },
];

const S = { maxWidth: "680px", margin: "0 auto", padding: "2rem 1rem", fontFamily: "-apple-system, sans-serif" };
const H = { textAlign: "center", marginBottom: "2rem" };

export default function App() {
  const [operatorId, setOperatorId] = useState(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [completed, setCompleted] = useState(new Set([1]));
  const [error, setError] = useState("");

  async function handleRegister(data) {
    setError("");
    try {
      const resp = await fetch("/operator/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const json = await resp.json();
      if (!resp.ok) { setError(json.detail || "Registration failed"); return; }
      setOperatorId(json.operatorId);
      setCurrentStep(2);
    } catch { setError("Cannot reach API"); }
  }

  async function handleStep(stepNum, data) {
    if (stepNum === 1) { handleRegister(data); return; }
    setError("");
    try {
      const resp = await fetch(`/operator/step/${operatorId}/${stepNum}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const json = await resp.json();
      if (!resp.ok) { setError(json.detail || "Step failed"); return; }
      setCompleted(prev => new Set([...prev, stepNum]));
      if (stepNum < 8) setCurrentStep(stepNum + 1);
    } catch { setError("Cannot reach API"); }
  }

  const allDone = completed.size === 8;

  return (
    <div style={S}>
      <div style={H}>
        <h1>Operator Onboarding</h1>
        <p style={{ color: "#666" }}>
          {allDone ? "Onboarding complete!" : `Step ${currentStep} of 8 — ${STEPS[currentStep - 1].name}`}
        </p>
        {operatorId && <p style={{ fontSize: "0.85rem", color: "#999" }}>ID: {operatorId}</p>}
        <div style={{ display: "flex", gap: "4px", justifyContent: "center", margin: "1rem 0" }}>
          {STEPS.map(s => (
            <div key={s.num} onClick={() => (completed.has(s.num) || s.num <= currentStep) && setCurrentStep(s.num)}
              style={{ width: 32, height: 32, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 600, cursor: "pointer",
                background: completed.has(s.num) ? "#1d9e75" : s.num === currentStep ? "#7f77dd" : "#e0e0e0",
                color: completed.has(s.num) || s.num === currentStep ? "#fff" : "#666",
              }}>{s.num}</div>
          ))}
        </div>
      </div>
      {error && <p style={{ color: "red", textAlign: "center" }}>{error}</p>}
      <WizardStep step={STEPS[currentStep - 1]} onSubmit={(data) => handleStep(currentStep, data)}
        isCompleted={completed.has(currentStep)} isLast={currentStep === 8} />
    </div>
  );
}
