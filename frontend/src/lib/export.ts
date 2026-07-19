import * as XLSX from "xlsx";

export function exportToCsv<T extends Record<string, unknown>>(
  rows: T[],
  filename: string,
): void {
  if (rows.length === 0) {
    return;
  }
  const headers = Object.keys(rows[0]);
  const lines = [headers.join(",")];
  for (const row of rows) {
    const cells = headers.map((header) => {
      const value = row[header];
      const text = String(value ?? "").replace(/"/g, '""');
      return `"${text}"`;
    });
    lines.push(cells.join(","));
  }

  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${filename}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export function exportToExcel<T extends Record<string, unknown>>(
  rows: T[],
  filename: string,
): void {
  if (rows.length === 0) {
    return;
  }
  const worksheet = XLSX.utils.json_to_sheet(rows);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Data");
  XLSX.writeFile(workbook, `${filename}.xlsx`);
}
