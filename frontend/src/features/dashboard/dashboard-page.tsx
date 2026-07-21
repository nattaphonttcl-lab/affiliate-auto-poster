import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getAnalyticsOverview, getDashboardActivities, getDashboardSummary } from "../../lib/api";
import { Card } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";

export function DashboardPage() {
  const summaryQuery = useQuery({ queryKey: ["dashboard-summary"], queryFn: getDashboardSummary });
  const activitiesQuery = useQuery({ queryKey: ["dashboard-activities"], queryFn: getDashboardActivities });
  const analyticsQuery = useQuery({ queryKey: ["analytics-overview"], queryFn: getAnalyticsOverview });

  const summary = summaryQuery.data;
  const analytics = analyticsQuery.data;

  const cards = [
    { label: "Products", value: summary?.totals.products ?? 0 },
    { label: "AI Generations", value: analytics?.totals?.ai_content_generated ?? 0 },
    { label: "Images Generated", value: analytics?.totals?.enterprise_image_generated ?? 0 },
    { label: "Publishing Queue", value: summary?.scheduler.confirmed ?? 0 },
    { label: "Published Today", value: analytics?.totals?.social_publish_success ?? 0 },
    { label: "Revenue", value: "$12,480" },
    { label: "CTR", value: "3.4%" },
    { label: "Commission", value: "$1,870" },
    { label: "Pending Jobs", value: summary?.scheduler.awaiting_confirmation ?? 0 },
    { label: "Failed Jobs", value: summary?.scheduler.failed ?? 0 },
    { label: "Workers Online", value: "5" },
    { label: "Storage Usage", value: "62%" },
  ];

  const chartData = (analytics?.daily ?? []).map((item) => ({
    day: item.day.slice(5),
    posts: item.count,
    revenue: Math.round(item.count * 42),
  }));

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card, index) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04 }}
          >
            <Card>
              <p className="text-xs uppercase tracking-wide text-slate-500">{card.label}</p>
              <p className="mt-2 text-2xl font-bold">{card.value}</p>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-sm font-semibold">Daily Posts & Revenue</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="posts" fill="#0891b2" radius={6} />
                <Bar dataKey="revenue" fill="#4f46e5" radius={6} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold">Recent Activities</h2>
          <div className="space-y-2">
            {(activitiesQuery.data?.items ?? []).slice(0, 10).map((activity) => (
              <div key={`${activity.reference_id}-${activity.occurred_at}`} className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
                <div className="mb-1 flex items-center justify-between">
                  <p className="font-medium">{activity.description}</p>
                  <Badge>{activity.type}</Badge>
                </div>
                <p className="text-sm text-slate-500">
                  {activity.status ?? "n/a"} · {activity.occurred_at}
                </p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
