import { useState, type FormEvent } from "react";

import { api } from "../api";
import type { QueryRow, ResultCandidate } from "../types";

interface Props {
  query: QueryRow;
  candidate?: ResultCandidate;
  onClose: () => void;
  onSaved: (candidate: ResultCandidate) => void;
}

function fileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export function CandidateEditor({ query, candidate, onClose, onSaved }: Props) {
  const [videoId, setVideoId] = useState(candidate?.video_id ?? "");
  const [frames, setFrames] = useState(
    Array.isArray(candidate?.img_id)
      ? candidate.img_id.join(", ")
      : String(candidate?.img_id ?? ""),
  );
  const [answer, setAnswer] = useState(candidate?.answer ?? "");
  const [note, setNote] = useState(candidate?.note ?? "");
  const [image, setImage] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const parsedFrames = frames
        .split(",")
        .map((part) => Number(part.trim()))
        .filter((value) => !Number.isNaN(value));
      const imgId =
        query.query_type === "trake" ? parsedFrames : parsedFrames[0];
      if (imgId === undefined || (Array.isArray(imgId) && imgId.length === 0)) {
        throw new Error("Hãy nhập frame hợp lệ");
      }
      const common: Record<string, unknown> = {
        img_id: imgId,
        video_id: videoId,
        note: note || null,
      };
      if (query.query_type === "qa") common.answer = answer;
      let saved: ResultCandidate;
      if (candidate) {
        saved = await api.updateResult(candidate.id, {
          ...common,
          expected_version: candidate.version,
        });
      } else {
        const body: Record<string, unknown> = {
          ...common,
          file_name: query.file_name,
          submitter: "UI",
        };
        if (image) {
          body.image_base64 = await fileAsDataUrl(image);
          body.image_mime_type = image.type;
        }
        saved = await api.createResult(body);
      }
      onSaved(saved);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể lưu kết quả",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="modal-card editor"
        role="dialog"
        aria-modal="true"
        aria-labelledby="candidate-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-heading">
          <div>
            <p className="eyebrow">{query.query_type.toUpperCase()}</p>
            <h2 id="candidate-title">
              {candidate ? "Chỉnh sửa candidate" : "Thêm candidate"}
            </h2>
          </div>
          <button
            className="icon-button"
            type="button"
            onClick={onClose}
            aria-label="Đóng"
          >
            ×
          </button>
        </div>
        <form onSubmit={submit}>
          <label>
            Video ID
            <input
              value={videoId}
              onChange={(event) => setVideoId(event.target.value)}
              required
            />
          </label>
          <label>
            {query.query_type === "trake"
              ? "Frames (phân cách bằng dấu phẩy)"
              : "Frame"}
            <input
              value={frames}
              onChange={(event) => setFrames(event.target.value)}
              required
            />
          </label>
          {query.query_type === "qa" && (
            <label>
              Answer
              <textarea
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                required
              />
            </label>
          )}
          <label>
            Ghi chú
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
          {!candidate && (
            <label>
              Ảnh kiểm tra (tùy chọn)
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(event) => setImage(event.target.files?.[0] ?? null)}
              />
            </label>
          )}
          {error && (
            <p className="error-banner" role="alert">
              {error}
            </p>
          )}
          <div className="modal-actions">
            <button
              className="button secondary"
              type="button"
              onClick={onClose}
            >
              Hủy
            </button>
            <button className="button primary" type="submit" disabled={saving}>
              {saving ? "Đang lưu…" : "Lưu candidate"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
