import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: "0.0.0.0",
    /* Proxy API calls to the FastAPI sandbox backend */
    proxy: {
      "/sim-swap": "http://localhost:8080",
      "/number-verification": "http://localhost:8080",
      "/location-verification": "http://localhost:8080",
      "/sandbox": "http://localhost:8080",
      "/health": "http://localhost:8080",
    },
  },
});
