import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Outlet } from "react-router-dom";

import { AppRouter } from "../../app/router";
import { AuthProvider } from "./auth-context";

import { ThemeProvider } from "../../app/theme-context";

const dashboardMarker = "Dashboard Marker";

vi.mock("../dashboard/dashboard-page", () => ({
  DashboardPage: () => <div>{dashboardMarker}</div>,
}));

vi.mock("../auth/password-change-page", () => ({
  PasswordChangePage: () => <div>Password Change</div>,
}));

vi.mock("../ai-studio/ai-studio-page", () => ({ AiStudioPage: () => <div /> }));
vi.mock("../analytics/analytics-page", () => ({ AnalyticsPage: () => <div /> }));
vi.mock("../calendar/calendar-page", () => ({ CalendarPage: () => <div /> }));
vi.mock("../dashboard/system-page", () => ({ SystemPage: () => <div /> }));
vi.mock("../files/files-page", () => ({ FilesPage: () => <div /> }));
vi.mock("../image-studio/image-studio-page", () => ({ ImageStudioPage: () => <div /> }));
vi.mock("../products/products-page", () => ({ ProductsPage: () => <div /> }));
vi.mock("../publishing/publishing-page", () => ({ PublishingPage: () => <div /> }));
vi.mock("../settings/settings-page", () => ({ SettingsPage: () => <div /> }));
vi.mock("../users/users-page", () => ({ UsersPage: () => <div /> }));
vi.mock("../../components/layout/app-shell", () => ({
  AppShell: () => (
    <div>
      <Outlet />
    </div>
  ),
}));

async function renderRouter(initialEntry: string, singleUserMode: string | undefined) {
  if (singleUserMode === undefined) {
    vi.unstubAllEnvs();
  } else {
    vi.stubEnv("SINGLE_USER_MODE", singleUserMode);
  }

  render(
    <QueryClientProvider client={new QueryClient()}>
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter initialEntries={[initialEntry]}>
            <AppRouter />
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

describe("single user mode", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.unstubAllEnvs();
  });

  it("opens dashboard immediately when enabled", async () => {
    await renderRouter("/login", "true");
    expect(await screen.findByText(dashboardMarker)).toBeInTheDocument();
  });

  it("shows login screen when authentication is enabled", async () => {
    await renderRouter("/login", "false");
    expect(await screen.findByText("Sign in to continue")).toBeInTheDocument();
  });

  it("switches between modes without breaking routing", async () => {
    await renderRouter("/dashboard", "true");
    expect(await screen.findByText(dashboardMarker)).toBeInTheDocument();

    localStorage.clear();
    await renderRouter("/dashboard", "false");
    expect(await screen.findByText("Sign in to continue")).toBeInTheDocument();
  });
});