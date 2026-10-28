import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The app is written against React's API but ships Preact (~4x smaller), which matters on
// phones on mobile data. Remove the aliases to ship real React instead.
const preact = {
  react: "preact/compat",
  "react-dom/client": "preact/compat/client",
  "react-dom": "preact/compat",
  "react/jsx-runtime": "preact/jsx-runtime",
};

// In development the API runs separately (python -m fantasy_bot.api); Vite proxies to it.
// In production the API serves the built files from web/dist itself.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: preact },
  server: {
    host: true, // reachable from a phone on the same Wi-Fi
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
  build: { target: "es2022", cssMinify: true },
});
