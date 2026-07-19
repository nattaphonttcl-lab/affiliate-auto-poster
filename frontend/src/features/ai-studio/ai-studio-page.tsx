import { useQuery } from "@tanstack/react-query";

import { getAiHistory, getAiTemplates } from "../../lib/api";
import { Card } from "../../components/ui/card";

export function AiStudioPage() {
  const templatesQuery = useQuery({ queryKey: ["ai-templates"], queryFn: getAiTemplates });
  const historyQuery = useQuery({ queryKey: ["ai-history"], queryFn: getAiHistory });

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <h2 className="mb-3 text-sm font-semibold">Prompt Templates</h2>
        <div className="space-y-2">
          {(templatesQuery.data ?? []).map((item: { id: number; name: string; category: string; status: string }) => (
            <div key={item.id} className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
              <p className="font-medium">{item.name}</p>
              <p className="text-sm text-slate-500">{item.category} · {item.status}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold">Generation History</h2>
        <div className="space-y-2">
          {(historyQuery.data?.items ?? []).map((item: { id: number; platform: string; style: string; current_version: number }) => (
            <div key={item.id} className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
              <p className="font-medium">{item.platform}</p>
              <p className="text-sm text-slate-500">
                {item.style} · version {item.current_version}
              </p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
