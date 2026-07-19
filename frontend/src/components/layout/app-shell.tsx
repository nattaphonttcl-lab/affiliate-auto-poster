import { useState } from "react";
import { Outlet } from "react-router-dom";

import { Breadcrumb } from "./breadcrumb";
import { CommandPalette } from "./command-palette";
import { NotificationCenter } from "./notification-center";
import { Sidebar } from "./sidebar";
import { TopNav } from "./top-nav";
import { ErrorBoundary } from "../ui/error-boundary";

export function AppShell() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-100 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopNav
          onOpenPalette={() => setPaletteOpen(true)}
          onToggleNotifications={() =>
            setNotificationsOpen((current) => !current)
          }
        />
        <Breadcrumb />
        <main className="flex-1 px-4 pb-6">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>

      <NotificationCenter open={notificationsOpen} />
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
}
