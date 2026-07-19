import { Bell, Command, Moon, Search, Sun } from "lucide-react";
import { useState } from "react";

import { Button } from "../ui/button";
import { useTheme } from "../../app/theme-context";

type Props = {
  onOpenPalette: () => void;
  onToggleNotifications: () => void;
};

export function TopNav({ onOpenPalette, onToggleNotifications }: Props) {
  const { theme, toggleTheme } = useTheme();
  const [query, setQuery] = useState("");

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90">
      <div className="flex items-center gap-3">
        <div className="relative w-full max-w-xl">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Global search: products, jobs, templates..."
            className="w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
          />
        </div>

        <Button variant="secondary" onClick={onOpenPalette}>
          <Command className="mr-1 h-4 w-4" />
          Command
        </Button>

        <Button variant="secondary" onClick={onToggleNotifications}>
          <Bell className="h-4 w-4" />
        </Button>

        <Button variant="secondary" onClick={toggleTheme}>
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  );
}
