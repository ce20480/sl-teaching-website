import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { WagmiConfig } from "wagmi";
import reportWebVitals from "@/reportWebVitals";
import { wagmiConfig } from "./lib/wagmi";

// Initialize polyfills
import { Buffer } from "buffer";
import process from "process";
import { TextEncoder } from "util";

// Set up global polyfills
window.Buffer = Buffer;
window.process = process;

// Only set TextEncoder if it's not already defined
if (typeof window.TextEncoder === "undefined") {
  window.TextEncoder = TextEncoder;
}

// Render the app
const root = ReactDOM.createRoot(
  document.getElementById("root") as HTMLElement
);

root.render(
  <React.StrictMode>
    <WagmiConfig config={wagmiConfig}>
      <App />
    </WagmiConfig>
  </React.StrictMode>
);

// Performance measurement
reportWebVitals();
