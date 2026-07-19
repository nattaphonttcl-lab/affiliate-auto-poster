import { QueryClientProvider } from "@tanstack/react-query";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { Toaster } from "sonner";
import type { PropsWithChildren } from "react";

import { queryClient } from "../lib/query-client";
import { AuthProvider } from "../features/auth/auth-context";
import { ThemeProvider } from "./theme-context";

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <DndProvider backend={HTML5Backend}>{children}</DndProvider>
          <Toaster richColors position="top-right" />
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
