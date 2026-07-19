import { useQuery } from "@tanstack/react-query";

import { Card } from "../../components/ui/card";
import { getHealth } from "../../lib/api";
import { useRealtime } from "../../hooks/use-realtime";

export function SystemPage() {
  const healthQuery = useQuery({ queryKey: ["health"], queryFn: getHealth });
  const realtime = useRealtime();

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <h2 className="mb-2 text-sm font-semibold">System Health</h2>
        <p className="text-sm text-slate-500">{JSON.stringify(healthQuery.data)}</p>
      </Card>
      <Card>
        <h2 className="mb-2 text-sm font-semibold">Realtime Status</h2>
        <p className="text-sm">WebSocket: {realtime.connected ? "connected" : "disconnected"}</p>
        <div className="mt-3 space-y-2">
          {realtime.messages.slice(0, 5).map((message) => (
            <div key={`${message.type}-${message.timestamp}`} className="rounded bg-slate-100 p-2 text-xs dark:bg-slate-800">
              {message.type} · {message.timestamp}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
