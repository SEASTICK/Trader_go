import React from "react";
import ReactDOM from "react-dom/client";
import UniverseApp from "./UniverseApp";
import "@fontsource-variable/inter";
import "./theme.css";
import "./universe.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <UniverseApp />
  </React.StrictMode>
);
