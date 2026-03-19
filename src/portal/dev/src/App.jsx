/**
 * App.jsx — Main application shell for the developer portal.
 *
 * Flow: Landing → Get API Key → Live Playground → SDK Snippets.
 * All sections on one page (tabbed). API key state flows from
 * ApiKeyForm to Playground to SnippetDisplay.
 */
import React, { useState } from "react";
import ApiKeyForm from "./components/ApiKeyForm";
import Playground from "./components/Playground";
import SnippetDisplay from "./components/SnippetDisplay";

const TABS = ["Get Started", "Playground", "SDK Snippets"];

export default function App() {
  const [apiKey, setApiKey] = useState("");
  const [activeTab, setActiveTab] = useState(0);
  const [lastResponse, setLastResponse] = useState(null);
  const [lastSurface, setLastSurface] = useState("");

  return (
    <div className="app">
      <header>
        <h1>CAMARA Canada Sandbox</h1>
        <p className="subtitle">
          Test SIM swap, number verification, and device location APIs against
          realistic Rogers / Bell / Telus simulation — no carrier agreement needed.
        </p>
      </header>

      <nav className="tabs">
        {TABS.map((tab, i) => (
          <button
            key={tab}
            className={activeTab === i ? "tab active" : "tab"}
            onClick={() => setActiveTab(i)}
          >
            {tab}
          </button>
        ))}
      </nav>

      <main>
        {activeTab === 0 && (
          <ApiKeyForm
            apiKey={apiKey}
            onKeyIssued={(key) => {
              setApiKey(key);
              setActiveTab(1);
            }}
          />
        )}
        {activeTab === 1 && (
          <Playground
            apiKey={apiKey}
            onResponse={(resp, surface) => {
              setLastResponse(resp);
              setLastSurface(surface);
            }}
          />
        )}
        {activeTab === 2 && (
          <SnippetDisplay
            apiKey={apiKey}
            lastResponse={lastResponse}
            surface={lastSurface}
          />
        )}
      </main>

      <footer>
        <p>
          Apache 2.0 · <a href="https://github.com/KachaJugaad/camara-dev">GitHub</a> · CAMARA Fall25 spec-compliant
        </p>
      </footer>
    </div>
  );
}
