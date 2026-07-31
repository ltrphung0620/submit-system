import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api, websocketUrl } from "./api";
import { ApiRequestTester } from "./components/ApiRequestTester";
import { CandidateEditor } from "./components/CandidateEditor";
import { QueryCard } from "./components/QueryCard";
import { applyRealtimeEvent } from "./state";
import type { QueryRow, RealtimeEvent, ResultCandidate } from "./types";

export default function App() {
  const [queries, setQueries] = useState<QueryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [submitterFilter, setSubmitterFilter] = useState("all");
  const [exporting, setExporting] = useState(false);
  const [exportingQueryId, setExportingQueryId] = useState<string | null>(null);
  const [swappingResultIds, setSwappingResultIds] = useState<string[]>([]);
  const [editing, setEditing] = useState<{
    query: QueryRow;
    candidate: ResultCandidate;
  } | null>(null);
  const queriesRef = useRef<QueryRow[]>([]);

  const refresh = useCallback(async () => {
    try {
      const next = await api.listQueries();
      queriesRef.current = next;
      setQueries(next);
      setError("");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể tải dữ liệu",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    queriesRef.current = queries;
  }, [queries]);

  useEffect(() => {
    let socket: WebSocket | undefined;
    let retry: number | undefined;
    let stopped = false;
    let attempt = 0;
    const connect = () => {
      socket = new WebSocket(websocketUrl());
      socket.onopen = () => {
        attempt = 0;
        void refresh();
      };
      socket.onmessage = (event) => {
        const message = JSON.parse(String(event.data)) as RealtimeEvent;
        const createdQueryId =
          message.event === "created" && "query_id" in message.data
            ? String(message.data.query_id)
            : null;
        if (
          message.event === "query_set_imported" ||
          (createdQueryId &&
            !queriesRef.current.some((query) => query.id === createdQueryId))
        )
          void refresh();
        else setQueries((current) => applyRealtimeEvent(current, message));
      };
      socket.onclose = () => {
        if (!stopped) {
          const delay = Math.min(1000 * 2 ** attempt++, 15000);
          retry = window.setTimeout(connect, delay);
        }
      };
    };
    connect();
    return () => {
      stopped = true;
      if (retry) window.clearTimeout(retry);
      socket?.close();
    };
  }, [refresh]);

  const submittedQueries = useMemo(
    () => queries.filter((query) => query.results.length > 0),
    [queries],
  );
  const submitters = useMemo(
    () =>
      Array.from(
        new Set(
          submittedQueries.flatMap((query) =>
            query.results.map((result) => result.submitter),
          ),
        ),
      ).sort(),
    [submittedQueries],
  );
  const filtered = useMemo(() => {
    const needle = search.toLocaleLowerCase();
    return submittedQueries.filter((query) => {
      const haystack = `${query.file_name} ${query.content} ${query.results
        .map((result) => result.submitter)
        .join(" ")}`.toLocaleLowerCase();
      return (
        haystack.includes(needle) &&
        (typeFilter === "all" || query.query_type === typeFilter) &&
        (submitterFilter === "all" ||
          query.results.some((result) => result.submitter === submitterFilter))
      );
    });
  }, [search, submittedQueries, submitterFilter, typeFilter]);

  async function deleteCandidate(candidate: ResultCandidate) {
    if (!window.confirm(`Xóa candidate ưu tiên ${candidate.priority}?`)) return;
    try {
      await api.deleteResult(candidate);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể xóa");
    }
  }

  async function downloadSubmissionZip() {
    setExporting(true);
    try {
      await api.downloadSubmissionZip();
      setError("");
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể tạo submission.zip",
      );
    } finally {
      setExporting(false);
    }
  }

  async function downloadQueryCsv(query: QueryRow) {
    setExportingQueryId(query.id);
    try {
      await api.downloadQueryCsv(query.id, query.file_name);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể xuất CSV");
    } finally {
      setExportingQueryId(null);
    }
  }

  async function swapPriorities(
    first: ResultCandidate,
    second: ResultCandidate,
  ) {
    setSwappingResultIds([first.id, second.id]);
    try {
      const swapped = await api.swapPriorities(first, second);
      setQueries((current) =>
        swapped.reduce(
          (next, candidate) =>
            applyRealtimeEvent(next, {
              schema_version: 1,
              event: "updated",
              occurred_at: new Date().toISOString(),
              data: candidate,
            }),
          current,
        ),
      );
      setError("");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể đổi priority",
      );
    } finally {
      setSwappingResultIds([]);
    }
  }

  async function reorderPriorities(
    query: QueryRow,
    orderedResults: ResultCandidate[],
  ) {
    setSwappingResultIds(query.results.map((result) => result.id));
    try {
      const reordered = await api.reorderPriorities(query, orderedResults);
      setQueries((current) =>
        current.map((item) =>
          item.id === query.id ? { ...item, results: reordered } : item,
        ),
      );
      setError("");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể sắp lại priority",
      );
      await refresh();
    } finally {
      setSwappingResultIds([]);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a
          className="brand"
          href="#main"
          aria-label="Hệ thống nộp bài AIC 2026"
        >
          <span className="brand-mark">AIC</span>
          <strong>Hệ thống nộp bài AIC 2026</strong>
        </a>
      </header>

      <main id="main">
        <ApiRequestTester
          onSubmitted={async (result) => {
            if (
              queriesRef.current.some((query) => query.id === result.query_id)
            ) {
              setQueries((current) =>
                applyRealtimeEvent(current, {
                  schema_version: 1,
                  event: "created",
                  occurred_at: new Date().toISOString(),
                  data: result,
                }),
              );
            } else {
              await refresh();
            }
          }}
        />

        {error && (
          <p className="error-banner" role="alert">
            {error}
          </p>
        )}

        <section className="workspace" aria-labelledby="queries-title">
          <div className="workspace-heading">
            <div>
              <p className="eyebrow">Public API · realtime</p>
              <h2 id="queries-title">Luồng submission</h2>
            </div>
            <div className="workspace-actions">
              <span className="query-count">
                {filtered.length} / {submittedQueries.length} nhóm ·{" "}
                {submittedQueries.reduce(
                  (total, query) => total + query.results.length,
                  0,
                )}{" "}
                request
              </span>
              <button
                className="button secondary"
                onClick={() => void downloadSubmissionZip()}
                disabled={!submittedQueries.length || exporting}
              >
                {exporting ? "Đang tạo ZIP…" : "Xuất submission.zip"}
              </button>
            </div>
          </div>
          <div className="filters" aria-label="Bộ lọc query">
            <label className="search">
              <span>Tìm</span>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Tên file, nội dung query hoặc người gửi"
              />
            </label>
            <label>
              <span>Loại</span>
              <select
                value={typeFilter}
                onChange={(event) => setTypeFilter(event.target.value)}
              >
                <option value="all">Tất cả</option>
                <option value="kis">KIS</option>
                <option value="qa">QA</option>
                <option value="trake">TRAKE</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
            <label>
              <span>Người nộp</span>
              <select
                value={submitterFilter}
                onChange={(event) => setSubmitterFilter(event.target.value)}
              >
                <option value="all">Tất cả</option>
                {submitters.map((name) => (
                  <option key={name}>{name}</option>
                ))}
              </select>
            </label>
          </div>

          {loading ? (
            <div className="state-card" aria-busy="true">
              Đang tải submission…
            </div>
          ) : filtered.length === 0 ? (
            <div className="state-card">
              <b>Chưa có submission nào</b>
              <p>
                Dùng form test phía trên hoặc gửi request đến POST
                /api/v1/submissions.
              </p>
            </div>
          ) : (
            <div className="query-grid">
              {filtered.map((query, index) => (
                <QueryCard
                  key={query.id}
                  index={index + 1}
                  query={query}
                  onEdit={(value, candidate) =>
                    setEditing({ query: value, candidate })
                  }
                  onDelete={(candidate) => void deleteCandidate(candidate)}
                  onExport={(value) => void downloadQueryCsv(value)}
                  exporting={exportingQueryId === query.id}
                  onSwap={(first, second) => void swapPriorities(first, second)}
                  onReorder={(value, orderedResults) =>
                    void reorderPriorities(value, orderedResults)
                  }
                  swappingResultIds={swappingResultIds}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      {editing && (
        <CandidateEditor
          query={editing.query}
          candidate={editing.candidate}
          onClose={() => setEditing(null)}
          onSaved={(saved) => {
            setQueries((current) =>
              applyRealtimeEvent(current, {
                schema_version: 1,
                event: "updated",
                occurred_at: new Date().toISOString(),
                data: saved,
              }),
            );
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}
