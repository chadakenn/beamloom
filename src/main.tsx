import React from "react";
import { createRoot } from "react-dom/client";
import { Player } from "@/components/studio/player";
import { Studio } from "@/components/studio/studio";
import "./styles.css";

const player = new URLSearchParams(window.location.search).has("player");

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>{player ? <Player /> : <Studio />}</React.StrictMode>,
);
