import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { AppShell } from "../components/layout/app-shell";
import { ThemeProvider } from "../app/theme-context";

vi.mock("../features/auth/auth-context", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { email: "test@example.com", role: "admin" },
    logout: vi.fn(),
  }),
}));

describe("AppShell", () => {
  it("renders navigation", () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ThemeProvider>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route path="/" element={<AppShell />}>
                <Route index element={<div>Page</div>} />
              </Route>
            </Routes>
          </MemoryRouter>
        </ThemeProvider>
      </QueryClientProvider>,
    );

    expect(screen.getByText("Affiliate Enterprise")).toBeInTheDocument();
  });
});
