import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../components/layout/app-shell";
import { LoginPage } from "../features/auth/login-page";
import { RequireAuth } from "../features/auth/require-auth";
import { AiStudioPage } from "../features/ai-studio/ai-studio-page";
import { AnalyticsPage } from "../features/analytics/analytics-page";
import { CalendarPage } from "../features/calendar/calendar-page";
import { DashboardPage } from "../features/dashboard/dashboard-page";
import { SystemPage } from "../features/dashboard/system-page";
import { FilesPage } from "../features/files/files-page";
import { ImageStudioPage } from "../features/image-studio/image-studio-page";
import { ProductsPage } from "../features/products/products-page";
import { PublishingPage } from "../features/publishing/publishing-page";
import { SettingsPage } from "../features/settings/settings-page";
import { UsersPage } from "../features/users/users-page";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/ai-studio" element={<AiStudioPage />} />
          <Route path="/image-studio" element={<ImageStudioPage />} />
          <Route path="/publishing" element={<PublishingPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/files" element={<FilesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/users" element={<UsersPage />} />
          <Route path="/system" element={<SystemPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
