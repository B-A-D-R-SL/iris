// AI contribution: 50% or more AI-generated
import React from "react";
import ReactDOM from "react-dom/client";

import "@mantine/core/styles.css";
import "./shared/i18n";

import App from "./app/App";
import { AppProviders } from "./app/providers";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppProviders>
      <App />
    </AppProviders>
  </React.StrictMode>,
);
