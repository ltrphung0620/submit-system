import { useRef, useState } from "react";
import type { DragEvent } from "react";

import type { QueryRow, ResultCandidate } from "../types";

interface Props {
  index: number;
  query: QueryRow;
  onEdit: (query: QueryRow, result: ResultCandidate) => void;
  onDelete: (result: ResultCandidate) => void;
  onExport: (query: QueryRow) => void;
  exporting: boolean;
  onSwap: (first: ResultCandidate, second: ResultCandidate) => void;
  onReorder: (query: QueryRow, orderedResults: ResultCandidate[]) => void;
  swappingResultIds: string[];
}

export function QueryCard({
  index,
  query,
  onEdit,
  onDelete,
  onExport,
  exporting,
  onSwap,
  onReorder,
  swappingResultIds,
}: Props) {
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dragTargetId, setDragTargetId] = useState<string | null>(null);
  const candidateListRef = useRef<HTMLDivElement>(null);
  if (query.results.length === 0) return null;

  function clearDragState() {
    setDraggedId(null);
    setDragTargetId(null);
  }

  function handleDragOver(event: DragEvent<HTMLElement>, targetId: string) {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    setDragTargetId(targetId);
    const list = candidateListRef.current;
    if (!list || typeof list.scrollBy !== "function") return;
    const bounds = list.getBoundingClientRect();
    if (event.clientX < bounds.left + 70) list.scrollBy({ left: -28 });
    if (event.clientX > bounds.right - 70) list.scrollBy({ left: 28 });
  }

  function handleDrop(event: DragEvent<HTMLElement>, targetId: string) {
    event.preventDefault();
    if (!draggedId || draggedId === targetId) {
      clearDragState();
      return;
    }
    const sourceIndex = query.results.findIndex(
      (result) => result.id === draggedId,
    );
    const targetIndex = query.results.findIndex(
      (result) => result.id === targetId,
    );
    if (sourceIndex < 0 || targetIndex < 0) {
      clearDragState();
      return;
    }
    const reordered = [...query.results];
    const [moved] = reordered.splice(sourceIndex, 1);
    reordered.splice(targetIndex, 0, moved);
    clearDragState();
    onReorder(query, reordered);
  }

  return (
    <article className="query-card">
      <div className="query-index">{String(index).padStart(2, "0")}</div>
      <div className="query-meta">
        <span className={`type-pill ${query.query_type}`}>
          {query.query_type.toUpperCase()}
        </span>
        <h2>{query.file_name}</h2>
        <p>{query.content}</p>
        <button
          className="button compact"
          onClick={() => onExport(query)}
          disabled={exporting}
        >
          {exporting ? "Đang xuất…" : "Xuất CSV"}
        </button>
      </div>
      <div className="candidate-list" ref={candidateListRef}>
        {query.results.map((result, resultIndex) => (
          <section
            className={`candidate${draggedId === result.id ? " dragging" : ""}${
              dragTargetId === result.id && draggedId !== result.id
                ? " drag-target"
                : ""
            }`}
            key={result.id}
            draggable={swappingResultIds.length === 0}
            onDragStart={(event) => {
              event.dataTransfer.effectAllowed = "move";
              event.dataTransfer.setData("text/plain", result.id);
              setDraggedId(result.id);
            }}
            onDragOver={(event) => handleDragOver(event, result.id)}
            onDrop={(event) => handleDrop(event, result.id)}
            onDragEnd={clearDragState}
            title="Giữ và kéo card đến vị trí priority mong muốn"
          >
            <div className="candidate-priority">
              <b>Priority #{result.priority}</b>
              <span className="drag-hint" aria-hidden="true">
                ⠿ Kéo
              </span>
              <div className="priority-actions">
                <button
                  className="text-button"
                  onClick={() => onSwap(result, query.results[resultIndex - 1])}
                  disabled={resultIndex === 0 || swappingResultIds.length > 0}
                  aria-label={`Đưa priority ${result.priority} lên trước`}
                >
                  ← Trước
                </button>
                <button
                  className="text-button"
                  onClick={() => onSwap(result, query.results[resultIndex + 1])}
                  disabled={
                    resultIndex === query.results.length - 1 ||
                    swappingResultIds.length > 0
                  }
                  aria-label={`Đưa priority ${result.priority} xuống sau`}
                >
                  Sau →
                </button>
              </div>
            </div>
            {result.image_url && (
              <a
                className="candidate-image"
                href={result.image_url}
                target="_blank"
                rel="noreferrer"
                aria-label={`Mở ảnh của ${query.file_name}, priority ${result.priority}`}
              >
                <img
                  src={result.image_url}
                  alt={`Ảnh của ${query.file_name}, priority ${result.priority}`}
                  loading="lazy"
                  decoding="async"
                  draggable={false}
                />
              </a>
            )}
            <dl className="result-fields">
              <div>
                <dt>video_id</dt>
                <dd>{result.video_id}</dd>
              </div>
              <div>
                <dt>img_id</dt>
                <dd>
                  {Array.isArray(result.img_id)
                    ? `[${result.img_id.join(", ")}]`
                    : result.img_id}
                </dd>
              </div>
              {query.query_type === "qa" && (
                <div>
                  <dt>answer</dt>
                  <dd>{result.answer ?? "—"}</dd>
                </div>
              )}
              <div>
                <dt>submitter</dt>
                <dd>{result.submitter}</dd>
              </div>
            </dl>
            <div className="candidate-footer">
              <div className="row-actions">
                <button
                  className="text-button"
                  onClick={() => onEdit(query, result)}
                >
                  Sửa
                </button>
                <button
                  className="text-button danger"
                  onClick={() => onDelete(result)}
                >
                  Xóa
                </button>
              </div>
            </div>
          </section>
        ))}
      </div>
    </article>
  );
}
