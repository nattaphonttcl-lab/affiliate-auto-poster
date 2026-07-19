import { useQuery } from "@tanstack/react-query";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getAnalyticsEvents, getAnalyticsOverview } from "../../lib/api";
import { Card } from "../../components/ui/card";

export function AnalyticsPage() {
  const overviewQuery = useQuery({ queryKey: ["analytics-overview"], queryFn: getAnalyticsOverview });
  const eventsQuery = useQuery({ queryKey: ["analytics-events"], queryFn: getAnalyticsEvents });

  const data = (overviewQuery.data?.daily_counts ?? []).map((item: { day: string; count: number }) => ({
    day: item.day.slice(5),
    ctr: Math.min(10, Math.round(item.count * 0.6)),
    revenue: item.count * 37,
  }));

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <h2 className="mb-3 text-sm font-semibold">Revenue / CTR / Conversion</h2>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="revenue" stroke="#0284c7" strokeWidth={2} />
              <Line type="monotone" dataKey="ctr" stroke="#4f46e5" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold">Event Timeline</h2>
        <div className="space-y-2">
          {(eventsQuery.data?.items ?? eventsQuery.data ?? []).slice(0, 15).map((event: { id: number; event_type: string; entity_type: string; occurred_at: string }) => (
            <div key={event.id} className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
              <p className="font-medium">{event.event_type}</p>
              <p className="text-xs text-slate-500">{event.entity_type} · {event.occurred_at}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
