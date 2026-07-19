import type { PropsWithChildren } from "react";

import { cn } from "../../lib/cn";

export function Badge({ children, className }: PropsWithChildren<{ className?: string }>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full bg-cyan-100 px-2 py-1 text-xs font-semibold text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-200",
        className,
      )}
    >
      {children}
    </span>
  );
}
