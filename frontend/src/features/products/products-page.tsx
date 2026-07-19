import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";

import { exportToCsv, exportToExcel } from "../../lib/export";
import { getProducts, refreshProduct } from "../../lib/api";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import type { Product } from "../../types/api";

const helper = createColumnHelper<Product>();

export function ProductsPage() {
  const queryClient = useQueryClient();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [search, setSearch] = useState("");

  const productsQuery = useQuery({ queryKey: ["products"], queryFn: getProducts });

  const refreshMutation = useMutation({
    mutationFn: refreshProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });

  const rows = useMemo(() => {
    const items = productsQuery.data ?? [];
    if (!search.trim()) {
      return items;
    }
    const q = search.toLowerCase();
    return items.filter((item) => item.title.toLowerCase().includes(q));
  }, [productsQuery.data, search]);

  const columns = useMemo(
    () => [
      helper.accessor("title", { header: "Title" }),
      helper.accessor("marketplace", { header: "Marketplace" }),
      helper.accessor("price", { header: "Price" }),
      helper.accessor("discount", { header: "Discount" }),
      helper.display({
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <Button
            variant="secondary"
            onClick={() => refreshMutation.mutate(row.original.id)}
          >
            Refresh
          </Button>
        ),
      }),
    ],
    [refreshMutation],
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search products"
          className="rounded-lg border border-slate-300 px-3 py-2"
        />
        <Button onClick={() => exportToCsv(rows, "products")}>CSV Export</Button>
        <Button variant="secondary" onClick={() => exportToExcel(rows, "products")}>Excel Export</Button>
      </div>

      <div className="overflow-auto rounded-xl border border-slate-200">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 dark:bg-slate-800">
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => (
                  <th key={header.id} className="px-3 py-2 text-left">
                    <button onClick={header.column.getToggleSortingHandler()}>
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </button>
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
