import React from "react";
import ReactDOM from "react-dom/client";
import ReactGA from "react-ga4";
import "./index.css";
import App from "./App";
import { QueryClientProvider } from "@tanstack/react-query";
import queryClient from "utils/reactQueryClient";

const gaMeasurementId = process.env.REACT_APP_GA_ID;

if (gaMeasurementId) {
  ReactGA.initialize(gaMeasurementId);
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
);
