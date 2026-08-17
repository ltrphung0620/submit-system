import { describe, expect, it } from "vitest";

import { collectExportWarnings } from "./exportWarnings";
import type { QueryRow, ResultCandidate } from "./types";

const candidate = (priority: number, note: string | null): ResultCandidate => ({
  id: `r${priority}`,
  query_id: "q-noted",
  file_name: "query-noted-kis",
  query_type: "kis",
  arrival_seq: priority,
  priority,
  video_id: "L21_V001",
  img_id: priority,
  answer: null,
  submitter: "UI",
  note,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  version: 1,
  structural_validation_status: "valid",
  official_validation_status: "unverified",
  image_url: null,
  image_mime_type: null,
});

describe("collectExportWarnings", () => {
  it("reports queries without answers and renders multiple candidate notes as a group", () => {
    const queries: QueryRow[] = [
      {
        id: "q-empty",
        query_set_id: "set-1",
        file_name: "query-empty-qa",
        query_type: "qa",
        content: "Câu hỏi",
        display_order: 1,
        source_path: "query-empty-qa.txt",
        results: [],
      },
      {
        id: "q-noted",
        query_set_id: "set-1",
        file_name: "query-noted-kis",
        query_type: "kis",
        content: "Câu hỏi khác",
        display_order: 2,
        source_path: "query-noted-kis.txt",
        results: [
          candidate(1, "Kiểm tra lại frame"),
          candidate(2, "Cần xác minh video"),
        ],
      },
    ];

    expect(collectExportWarnings(queries)).toEqual([
      {
        fileName: "query-empty-qa",
        notes: ["Chưa có đáp án"],
      },
      {
        fileName: "query-noted-kis",
        notes: [
          "Đáp án có độ ưu tiên thứ 1 có ghi chú là: Kiểm tra lại frame",
          "Đáp án có độ ưu tiên thứ 2 có ghi chú là: Cần xác minh video",
        ],
      },
    ]);
  });
});
