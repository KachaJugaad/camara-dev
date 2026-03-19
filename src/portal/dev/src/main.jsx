/**
 * main.jsx — Entry point for the CAMARA developer portal.
 *
 * Mounts the React app into the #root div.
 */
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./style.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
