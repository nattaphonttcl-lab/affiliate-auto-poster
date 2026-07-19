import { AlertTriangle, BellRing, CheckCircle2, Server } from "lucide-react";

import { Card } from "../ui/card";

const alerts = [
  { level: "success", text: "Publishing worker is healthy", icon: CheckCircle2 },
  { level: "warning", text: "3 jobs are waiting for retry", icon: AlertTriangle },
  { level: "info", text: "Realtime stream connected", icon: Server },
  { level: "info", text: "New analytics sync completed", icon: BellRing },
];

type Props = {
  open: boolean;
};

export function NotificationCenter({ open }: Props) {
  if (!open) {
    return null;
  }

  return (
    <aside className="fixed right-4 top-20 z-50 w-[360px]">
      <Card className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          Notification Center
        </h3>
        {alerts.map((alert) => {
          const Icon = alert.icon;
          return (
            <div
              key={alert.text}
              className="flex items-start gap-2 rounded-lg bg-slate-100 p-2 text-sm dark:bg-slate-800"
            >
              <Icon className="mt-0.5 h-4 w-4" />
              <p>{alert.text}</p>
            </div>
          );
        })}
      </Card>
    </aside>
  );
}
