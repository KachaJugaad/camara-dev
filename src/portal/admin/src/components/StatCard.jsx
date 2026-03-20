/**
 * StatCard.jsx — Single stat card for the admin dashboard.
 */
import React from "react";

const card = {
  background: "#fff",
  border: "1px solid #dee2e6",
  borderRadius: 8,
  padding: "1rem",
  textAlign: "center",
};

export default function StatCard({ label, value }) {
  return (
    <div style={card}>
      <div style={{ fontSize: 12, color: "#666", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, marginTop: 4 }}>{value}</div>
    </div>
  );
}
