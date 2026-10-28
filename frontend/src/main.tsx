// AI contribution: 50% or more AI-generated
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router";

// Inter is bundled with the app: no request to a font service (Law 25).
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@mantine/core/styles.css";
import "@mantine/dates/styles.css";
import "./shared/i18n";

import App from "./app/App";
import { AppProviders } from "./app/providers";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppProviders>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </AppProviders>
  </React.StrictMode>,
);
