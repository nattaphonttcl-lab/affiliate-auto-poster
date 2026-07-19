import { useQuery } from "@tanstack/react-query";

import { getImageHistory, getImageTemplates } from "../../lib/api";
import { Card } from "../../components/ui/card";

export function ImageStudioPage() {
  const templatesQuery = useQuery({ queryKey: ["image-templates"], queryFn: getImageTemplates });
  const historyQuery = useQuery({ queryKey: ["image-history"], queryFn: getImageHistory });

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <h2 className="mb-3 text-sm font-semibold">Template Browser</h2>
        <div className="space-y-2">
          {(templatesQuery.data ?? []).map((item: { id: number; name: string; image_type: string; status: string }) => (
            <div key={item.id} className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
              <p className="font-medium">{item.name}</p>
              <p className="text-sm text-slate-500">{item.image_type} · {item.status}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold">Image History & Versions</h2>
        <div className="space-y-2">
          {(historyQuery.data?.items ?? []).map((item: { generated_image_id: number; version: number; provider: string; preview_uri: string }) => (
            <div key={`${item.generated_image_id}-${item.version}`} className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
              <p className="font-medium">Image #{item.generated_image_id}</p>
              <p className="text-sm text-slate-500">Provider {item.provider} · v{item.version}</p>
              <a href={item.preview_uri} target="_blank" rel="noreferrer" className="text-xs text-indigo-600">
                Preview
              </a>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
