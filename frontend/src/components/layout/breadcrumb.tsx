import { useMemo } from "react";
import { useLocation } from "react-router-dom";

export function Breadcrumb() {
  const location = useLocation();
  const items = useMemo(
    () => location.pathname.split("/").filter(Boolean),
    [location.pathname],
  );

  return (
    <nav className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
      <ol className="flex flex-wrap items-center gap-2">
        <li>Home</li>
        {items.map((item) => (
          <li key={item} className="capitalize">
            / {item.replace(/-/g, " ")}
          </li>
        ))}
      </ol>
    </nav>
  );
}
