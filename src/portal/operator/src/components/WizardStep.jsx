/**
 * WizardStep.jsx — Single step in the operator onboarding wizard.
 *
 * Renders form fields for the current step and calls onSubmit with
 * the collected data. Handles text, number, and checkbox fields.
 */
import React, { useState } from "react";

const card = { background: "#fff", border: "1px solid #dee2e6", borderRadius: 8, padding: "1.5rem", marginBottom: "1rem" };
const btn = { padding: "0.6rem 1.5rem", background: "#0f3460", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: "0.9rem" };
const input = { display: "block", width: "100%", padding: "0.5rem", border: "1px solid #dee2e6", borderRadius: 4, marginTop: 4, marginBottom: 12, fontSize: "0.9rem" };

export default function WizardStep({ step, onSubmit, isCompleted, isLast }) {
  const [values, setValues] = useState({});

  function handleChange(key, val) {
    setValues(prev => ({ ...prev, [key]: val }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit(values);
  }

  if (step.fields.length === 0) {
    return (
      <div style={card}>
        <h3>{step.name}</h3>
        <p style={{ color: "#666", margin: "1rem 0" }}>
          {step.num === 7 ? "Click below to run conformance tests against your configuration." :
           "Click below to publish your carrier profile to the sandbox."}
        </p>
        <button style={btn} onClick={() => onSubmit({ confirmed: true })}>
          {isCompleted ? "Done" : isLast ? "Publish" : "Run Tests"}
        </button>
        {isCompleted && <p style={{ color: "#1d9e75", marginTop: 8 }}>Completed</p>}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} style={card}>
      <h3>{step.name}</h3>
      {step.fields.map(f => (
        <label key={f.key} style={{ display: "block", marginTop: 12, fontWeight: 500, fontSize: "0.9rem" }}>
          {f.label}
          {f.type === "checkbox" ? (
            <input type="checkbox" checked={!!values[f.key]}
              onChange={e => handleChange(f.key, e.target.checked)}
              style={{ marginLeft: 8 }} />
          ) : (
            <input type={f.type || "text"} placeholder={f.placeholder}
              value={values[f.key] || ""} onChange={e => handleChange(f.key, e.target.value)}
              style={input} />
          )}
        </label>
      ))}
      <button type="submit" style={btn}>
        {isCompleted ? "Update" : "Complete Step"}
      </button>
      {isCompleted && <span style={{ color: "#1d9e75", marginLeft: 12 }}>Completed</span>}
    </form>
  );
}
