import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { Providers } from "./app/Providers";
import { AppRoutes } from "./app/router";

const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element in index.html");

createRoot(root).render(
  <StrictMode>
    <Providers>
      <AppRoutes />
    </Providers>
  </StrictMode>
);
