import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api, websocketUrl } from "./api";
import { CandidateEditor } from "./components/CandidateEditor";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { ExportWarningsDialog } from "./components/ExportWarningsDialog";
import { QueryCard } from "./components/QueryCard";
import { QueryZipUploader } from "./components/QueryZipUploader";
import { collectExportWarnings, type ExportWarning } from "./exportWarnings";
import { applyRealtimeEvent } from "./state";
import type {
  AuthSession,
  QueryRow,
  RealtimeEvent,
  ResultCandidate,
} from "./types";

interface Props {
  authSession: AuthSession;
  onLogout: () => void;
}

type PendingDeletion =
  | { kind: "candidate"; candidate: ResultCandidate }
  | { kind: "query"; query: QueryRow }
  | { kind: "all_queries" };

export default function App({ authSession, onLogout }: Props) {
  const [queries, setQueries] = useState<QueryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [submitterFilter, setSubmitterFilter] = useState("all");
  const [exporting, setExporting] = useState(false);
  const [exportWarnings, setExportWarnings] = useState<ExportWarning[] | null>(null);
  const [deletingAllQueries, setDeletingAllQueries] = useState(false);
  const [exportingQueryId, setExportingQueryId] = useState<string | null>(null);
  const [swappingResultIds, setSwappingResultIds] = useState<string[]>([]);
  const [duplicatingResultIds, setDuplicatingResultIds] = useState<string[]>([]);
  const [pendingDeletion, setPendingDeletion] = useState<PendingDeletion | null>(null);
  const [confirmingDeletion, setConfirmingDeletion] = useState(false);
  const [editing, setEditing] = useState<{
    query: QueryRow;
    candidate?: ResultCandidate;
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
    const initialRefresh = window.setTimeout(() => {
      void refresh();
    }, 0);
    return () => window.clearTimeout(initialRefresh);
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
          message.event === "query_deleted" ||
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
          queries.flatMap((query) =>
            query.results.map((result) => result.submitter),
          ),
        ),
      ).sort(),
    [queries],
  );
  const filtered = useMemo(() => {
    const needle = search.toLocaleLowerCase();
    return queries.filter((query) => {
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
  }, [queries, search, submitterFilter, typeFilter]);

  async function deleteCandidate(candidate: ResultCandidate) {
    try {
      await api.deleteResult(candidate);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể xóa");
    }
  }

  async function duplicateCandidate(candidate: ResultCandidate) {
    setDuplicatingResultIds((current) => [...current, candidate.id]);
    try {
      const duplicate = await api.duplicateResult(candidate.id);
      setQueries((current) =>
        applyRealtimeEvent(current, {
          schema_version: 1,
          event: "created",
          occurred_at: new Date().toISOString(),
          data: duplicate,
        }),
      );
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể duplicate candidate");
    } finally {
      setDuplicatingResultIds((current) =>
        current.filter((resultId) => resultId !== candidate.id),
      );
    }
  }

  async function deleteQuery(query: QueryRow) {
    try {
      await api.deleteQuery(query.id);
      setQueries((current) => current.filter((item) => item.id !== query.id));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể xóa query");
    }
  }

  async function deleteAllQueries() {
    setDeletingAllQueries(true);
    try {
      await api.deleteAllQueries();
      setQueries([]);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể xóa toàn bộ query");
    } finally {
      setDeletingAllQueries(false);
    }
  }

  async function confirmDeletion() {
    if (!pendingDeletion || confirmingDeletion) return;
    setConfirmingDeletion(true);
    try {
      if (pendingDeletion.kind === "candidate") {
        await deleteCandidate(pendingDeletion.candidate);
      } else if (pendingDeletion.kind === "query") {
        await deleteQuery(pendingDeletion.query);
      } else {
        await deleteAllQueries();
      }
      setPendingDeletion(null);
    } finally {
      setConfirmingDeletion(false);
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

  function requestSubmissionZip() {
    const warnings = collectExportWarnings(queries);
    if (warnings.length) {
      setExportWarnings(warnings);
      return;
    }
    void downloadSubmissionZip();
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
        <div className="session-controls">
          {authSession.authenticated && (
            <button className="button secondary compact" onClick={onLogout}>
              Đăng xuất
            </button>
          )}
        </div>
      </header>

      <main id="main">
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
                {filtered.length} / {queries.length} query
              </span>
              <QueryZipUploader
                onImported={async () => {
                  await refresh();
                }}
              />
              <button
                className="button secondary"
                onClick={requestSubmissionZip}
                disabled={!queries.length || exporting}
              >
                {exporting ? "Đang tạo ZIP…" : "Xuất submission.zip"}
              </button>
              <button
                className="button danger-button"
                onClick={() => setPendingDeletion({ kind: "all_queries" })}
                disabled={!queries.length || deletingAllQueries}
              >
                {deletingAllQueries ? "Đang xóa…" : "Xóa toàn bộ query"}
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
          ) : queries.length === 0 ? (
            <div className="state-card">
              <b>Chưa có query nào</b>
              <p>
                Nạp file ZIP chứa query .txt để tạo các khung nộp bài.
              </p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="state-card">
              <b>Không có query phù hợp</b>
              <p>Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm.</p>
            </div>
          ) : (
            <div className="query-grid">
              {filtered.map((query, index) => (
                <QueryCard
                  key={query.id}
                  index={index + 1}
                  query={query}
                  onAddCandidate={(value) => setEditing({ query: value })}
                  onDeleteQuery={(value) => setPendingDeletion({ kind: "query", query: value })}
                  onEdit={(value, candidate) =>
                    setEditing({ query: value, candidate })
                  }
                  onDelete={(candidate) => setPendingDeletion({ kind: "candidate", candidate })}
                  onDuplicate={(candidate) => void duplicateCandidate(candidate)}
                  onExport={(value) => void downloadQueryCsv(value)}
                  exporting={exportingQueryId === query.id}
                  onSwap={(first, second) => void swapPriorities(first, second)}
                  onReorder={(value, orderedResults) =>
                    void reorderPriorities(value, orderedResults)
                  }
                  swappingResultIds={swappingResultIds}
                  duplicatingResultIds={duplicatingResultIds}
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
      {pendingDeletion && (
        <ConfirmDialog
          title={
            pendingDeletion.kind === "candidate"
              ? "Xóa candidate?"
              : pendingDeletion.kind === "query"
                ? "Xóa query?"
                : "Xóa toàn bộ query?"
          }
          message={
            pendingDeletion.kind === "candidate"
              ? `Candidate #${pendingDeletion.candidate.priority} sẽ bị xóa.`
              : pendingDeletion.kind === "query"
                ? `Query ${pendingDeletion.query.file_name} và toàn bộ candidate bên trong sẽ bị xóa.`
                : "Toàn bộ query và candidate bên trong sẽ bị xóa."
          }
          confirming={confirmingDeletion}
          onCancel={() => {
            if (!confirmingDeletion) setPendingDeletion(null);
          }}
          onConfirm={() => void confirmDeletion()}
        />
      )}
      {exportWarnings && (
        <ExportWarningsDialog
          warnings={exportWarnings}
          canContinue={submittedQueries.length > 0}
          onClose={() => setExportWarnings(null)}
          onContinue={() => {
            setExportWarnings(null);
            void downloadSubmissionZip();
          }}
        />
      )}
    </div>
  );
}
