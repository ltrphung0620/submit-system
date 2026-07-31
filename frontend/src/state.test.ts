import { describe, expect, it } from "vitest";

import { applyRealtimeEvent } from "./state";
import type { QueryRow, ResultCandidate } from "./types";

const candidate = (id: string, arrival_seq: number): ResultCandidate => ({
  id,
  query_id: "q1",
  file_name: "query-1-kis",
  query_type: "kis",
  arrival_seq,
  priority: arrival_seq,
  video_id: "L01_V001",
  img_id: arrival_seq,
  answer: null,
  submitter: "Định",
  note: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  version: 1,
  structural_validation_status: "valid",
  official_validation_status: "unverified",
  image_url: null,
  image_mime_type: null,
});

const query: QueryRow = {
  id: "q1",
  query_set_id: "set1",
  file_name: "query-1-kis",
  query_type: "kis",
  content: "query content",
  display_order: 1,
  source_path: "query-1-kis.txt",
  results: [candidate("r1", 1)],
};

describe("applyRealtimeEvent", () => {
  it("ignores unsupported schemas, query-set signals, and unrelated queries", () => {
    const unsupported = applyRealtimeEvent([query], {
      schema_version: 2,
      event: "created",
      occurred_at: "2026-01-01T00:00:01Z",
      data: candidate("r2", 2),
    });
    expect(unsupported).toEqual([query]);
    const imported = applyRealtimeEvent([query], {
      schema_version: 1,
      event: "query_set_imported",
      occurred_at: "2026-01-01T00:00:01Z",
      data: {},
    });
    expect(imported).toEqual([query]);
    const unrelated = applyRealtimeEvent([query], {
      schema_version: 1,
      event: "created",
      occurred_at: "2026-01-01T00:00:01Z",
      data: { ...candidate("r2", 2), query_id: "other" },
    });
    expect(unrelated).toEqual([query]);
  });

  it("adds candidates in backend priority order without duplicating HTTP/event copies", () => {
    const newer = candidate("r2", 2);
    const once = applyRealtimeEvent([query], {
      schema_version: 1,
      event: "created",
      occurred_at: "2026-01-01T00:00:01Z",
      data: newer,
    });
    const twice = applyRealtimeEvent(once, {
      schema_version: 1,
      event: "created",
      occurred_at: "2026-01-01T00:00:01Z",
      data: newer,
    });
    expect(twice[0].results.map((result) => result.id)).toEqual(["r1", "r2"]);
  });

  it("updates by id without changing arrival order and deletes by id", () => {
    const start = [
      { ...query, results: [candidate("r1", 1), candidate("r2", 2)] },
    ];
    const updated = { ...candidate("r1", 1), answer: "Bình Định", version: 2 };
    const afterUpdate = applyRealtimeEvent(start, {
      schema_version: 1,
      event: "updated",
      occurred_at: "2026-01-01T00:00:01Z",
      data: updated,
    });
    expect(afterUpdate[0].results.map((result) => result.id)).toEqual([
      "r1",
      "r2",
    ]);
    const afterDelete = applyRealtimeEvent(afterUpdate, {
      schema_version: 1,
      event: "deleted",
      occurred_at: "2026-01-01T00:00:02Z",
      data: { id: "r1", query_id: "q1" },
    });
    expect(afterDelete[0].results.map((result) => result.id)).toEqual(["r2"]);
  });

  it("orders candidates by mutable priority while preserving arrival sequence", () => {
    const start = [
      { ...query, results: [candidate("r1", 1), candidate("r2", 2)] },
    ];
    const firstMoved = applyRealtimeEvent(start, {
      schema_version: 1,
      event: "updated",
      occurred_at: "2026-01-01T00:00:01Z",
      data: { ...candidate("r1", 1), priority: 2, version: 2 },
    });
    const fullySwapped = applyRealtimeEvent(firstMoved, {
      schema_version: 1,
      event: "updated",
      occurred_at: "2026-01-01T00:00:02Z",
      data: { ...candidate("r2", 2), priority: 1, version: 2 },
    });
    expect(
      fullySwapped[0].results.map((result) => [
        result.id,
        result.priority,
        result.arrival_seq,
      ]),
    ).toEqual([
      ["r2", 1, 2],
      ["r1", 2, 1],
    ]);
  });
});
