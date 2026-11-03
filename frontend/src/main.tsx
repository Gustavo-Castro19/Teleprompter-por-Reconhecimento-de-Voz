import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import OnAirApp from "./OnAirApp.tsx";

const isOnAir = new URLSearchParams(window.location.search).has("onair");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {isOnAir ? <OnAirApp /> : <App />}
  </StrictMode>,
);
