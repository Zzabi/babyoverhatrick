import { ClerkProvider } from "@clerk/clerk-react";
import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { getRouter } from "./router";

const CLERK_PUBLISHABLE_KEY = (import.meta.env['VITE_CLERK_PUBLISHABLE_KEY'] as string | undefined) ?? "";

if (!CLERK_PUBLISHABLE_KEY) {
  console.warn("[clerk] VITE_CLERK_PUBLISHABLE_KEY not set — auth features disabled");
}

const router = getRouter();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ClerkProvider
      publishableKey={CLERK_PUBLISHABLE_KEY ?? "pk_test_placeholder"}
      afterSignOutUrl="/"
    >
      <RouterProvider router={router} />
    </ClerkProvider>
  </StrictMode>
);
