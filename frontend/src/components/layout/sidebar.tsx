import { NavLink } from "react-router-dom";

import { NAV_ITEMS } from "./nav-config";
import { cn } from "../../lib/cn";

export function Sidebar() {
  return (
    <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-slate-50 p-4 lg:block dark:border-slate-800 dark:bg-slate-950">
      <div className="rounded-xl bg-gradient-to-br from-cyan-500 to-indigo-600 p-4 text-white">
        <h2 className="text-lg font-semibold">Affiliate Enterprise</h2>
        <p className="mt-1 text-sm text-cyan-100">Operations Control Center</p>
      </div>

      <nav className="mt-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 transition hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800",
                  isActive &&
                    "bg-slate-200 font-semibold dark:bg-slate-800 dark:text-white",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
