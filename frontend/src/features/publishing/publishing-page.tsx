import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";

import { cancelPublish, getPublishingJobs, retryPublish } from "../../lib/api";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import type { PublishingJob } from "../../types/api";

const helper = createColumnHelper<PublishingJob>();

export function PublishingPage() {
  const queryClient = useQueryClient();
  const jobsQuery = useQuery({ queryKey: ["publishing-jobs"], queryFn: getPublishingJobs });
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const retryMutation = useMutation({
    mutationFn: retryPublish,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["publishing-jobs"] }),
  });
  const cancelMutation = useMutation({
    mutationFn: cancelPublish,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["publishing-jobs"] }),
  });

  const rows = useMemo(() => {
    const items = jobsQuery.data?.items ?? [];
    if (statusFilter === "all") {
      return items;
    }
    return items.filter((item) => item.status === statusFilter);
  }, [jobsQuery.data?.items, statusFilter]);

  const columns = [
    helper.accessor("id", { header: "Job" }),
    helper.accessor("platform", { header: "Platform" }),
    helper.accessor("post_type", { header: "Type" }),
    helper.accessor("status", { header: "Status" }),
    helper.accessor("retry_count", { header: "Retries" }),
    helper.display({
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => retryMutation.mutate(row.original.id)}>
            Retry
          </Button>
          <Button variant="ghost" onClick={() => cancelMutation.mutate(row.original.id)}>
            Cancel
          </Button>
        </div>
      ),
    }),
  ];

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <Card>
      <div className="mb-3 flex items-center gap-2">
        <label className="text-sm font-medium">Status</label>
        <select
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2"
        >
          <option value="all">All</option>
          <option value="pending">Pending</option>
          <option value="scheduled">Scheduled</option>
          <option value="publishing">Publishing</option>
          <option value="published">Published</option>
          <option value="retry">Retry</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
          <option value="expired">Expired</option>
        </select>
      </div>

      <div className="overflow-auto rounded-xl border border-slate-200">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 dark:bg-slate-800">
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => (
                  <th key={header.id} className="px-3 py-2 text-left">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-t border-slate-100">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-2">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
