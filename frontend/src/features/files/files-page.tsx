import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getImageHistory } from "../../lib/api";
import { Card } from "../../components/ui/card";

export function FilesPage() {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const imagesQuery = useQuery({ queryKey: ["image-history"], queryFn: getImageHistory });

  const storageItems = useMemo(
    () => (imagesQuery.data?.items ?? []).slice(0, 25),
    [imagesQuery.data?.items],
  );

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <h2 className="mb-3 text-sm font-semibold">Storage Browser</h2>
        <div className="space-y-2">
          {storageItems.map((item: { version: number; image_uri: string; thumbnail_uri: string }) => (
            <div key={`${item.image_uri}-${item.version}`} className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
              <p className="truncate text-xs">{item.image_uri}</p>
              <div className="mt-2 flex gap-2">
                <button
                  onClick={() => setPreviewUrl(item.thumbnail_uri)}
                  className="rounded bg-indigo-600 px-2 py-1 text-xs text-white"
                >
                  Preview
                </button>
                <button className="rounded bg-rose-600 px-2 py-1 text-xs text-white">
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold">Upload / Preview</h2>
        <input
          type="file"
          accept="image/*"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) {
              return;
            }
            const url = URL.createObjectURL(file);
            setPreviewUrl(url);
          }}
        />

        <div className="mt-4 rounded-xl border border-dashed border-slate-300 p-4">
          {previewUrl ? (
            <img src={previewUrl} alt="preview" className="max-h-96 rounded-lg" />
          ) : (
            <p className="text-sm text-slate-500">Choose a file to preview.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
