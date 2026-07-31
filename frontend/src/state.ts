import type { QueryRow, RealtimeEvent, ResultCandidate } from "./types";

export function applyRealtimeEvent(
  queries: QueryRow[],
  message: RealtimeEvent,
): QueryRow[] {
  if (message.schema_version !== 1 || message.event === "query_set_imported")
    return queries;
  const data = message.data as Partial<ResultCandidate> & {
    id: string;
    query_id: string;
  };
  return queries.map((query) => {
    if (query.id !== data.query_id) return query;
    if (message.event === "deleted") {
      return {
        ...query,
        results: query.results.filter((result) => result.id !== data.id),
      };
    }
    const candidate = data as ResultCandidate;
    const withoutCurrent = query.results.filter(
      (result) => result.id !== candidate.id,
    );
    return {
      ...query,
      results: [...withoutCurrent, candidate].sort(
        (left, right) =>
          left.priority - right.priority ||
          left.arrival_seq - right.arrival_seq,
      ),
    };
  });
}
