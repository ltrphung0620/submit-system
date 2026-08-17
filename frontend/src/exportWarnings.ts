import type { QueryRow } from "./types";

export interface ExportWarning {
  fileName: string;
  notes: string[];
}

export function collectExportWarnings(queries: QueryRow[]): ExportWarning[] {
  return queries.flatMap((query) => {
    const notes: string[] = [];
    if (query.results.length === 0) {
      notes.push("Chưa có đáp án");
    }
    for (const candidate of query.results) {
      const note = candidate.note?.trim();
      if (note) {
        notes.push(
          `Đáp án có độ ưu tiên thứ ${candidate.priority} có ghi chú là: ${note}`,
        );
      }
    }
    return notes.length ? [{ fileName: query.file_name, notes }] : [];
  });
}
