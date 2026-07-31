import { useMemo, useState, type FormEvent } from "react";

import { api } from "../api";
import type {
  ResultCandidate,
  SubmissionPayload,
  SubmissionQueryType,
} from "../types";
import {
  buildSubmissionPayload,
  type SubmissionDraft,
} from "./submissionPayload";

interface Props {
  onSubmitted: (result: ResultCandidate) => Promise<void> | void;
}

const DEFAULT_DRAFT: SubmissionDraft = {
  queryType: "kis",
  fileName: "synthetic-ui-test-kis",
  queryContent: "Tìm khoảnh khắc một người bước vào cửa hàng.",
  videoId: "L21_V001",
  frames: "24834",
  answer: "Bình Định",
  submitter: "UI",
  imageBase64: "",
};

function fileNameForType(
  fileName: string,
  queryType: SubmissionQueryType,
): string {
  const stem = fileName
    .trim()
    .replace(/-(kis|qa|trake)$/i, "")
    .replace(/\.txt$/i, "");
  return `${stem || "synthetic-ui-test"}-${queryType}`;
}

function draftPreview(draft: SubmissionDraft): SubmissionPayload {
  const frameValues = draft.frames
    .split(",")
    .map((part) => Number(part.trim()))
    .filter((value) => Number.isInteger(value) && value >= 0);
  const payload: SubmissionPayload = {
    file_name: draft.fileName,
    query_content: draft.queryContent,
    img_id: draft.queryType === "trake" ? frameValues : (frameValues[0] ?? 0),
    video_id: draft.videoId,
    submitter: draft.submitter,
  };
  if (draft.queryType === "qa") payload.answer = draft.answer;
  if (draft.imageBase64.trim()) {
    payload.image_base64 = `<base64 đã ẩn: ${draft.imageBase64.trim().length} ký tự>`;
  }
  return payload;
}

export function ApiRequestTester({ onSubmitted }: Props) {
  const [draft, setDraft] = useState(DEFAULT_DRAFT);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [response, setResponse] = useState<ResultCandidate | null>(null);
  const preview = useMemo(() => draftPreview(draft), [draft]);

  function chooseType(queryType: SubmissionQueryType) {
    setDraft((current) => ({
      ...current,
      queryType,
      fileName: fileNameForType(current.fileName, queryType),
      frames:
        queryType === "trake"
          ? current.frames.includes(",")
            ? current.frames
            : `${current.frames}, 25230, 25432`
          : current.frames.split(",")[0].trim(),
    }));
    setError("");
    setResponse(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setResponse(null);
    setSending(true);
    try {
      const result = await api.createSubmission(buildSubmissionPayload(draft));
      setResponse(result);
      await onSubmitted(result);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể gửi request.",
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="request-tester" aria-labelledby="request-tester-title">
      <div className="tester-heading">
        <h2 id="request-tester-title">Gửi thử một request</h2>
      </div>

      <div className="tester-layout">
        <form className="tester-form" onSubmit={submit}>
          <fieldset>
            <legend>Loại query</legend>
            <div className="type-selector">
              {(["kis", "qa", "trake"] as const).map((queryType) => (
                <button
                  key={queryType}
                  type="button"
                  className={draft.queryType === queryType ? "selected" : ""}
                  aria-pressed={draft.queryType === queryType}
                  onClick={() => chooseType(queryType)}
                >
                  {queryType.toUpperCase()}
                </button>
              ))}
            </div>
          </fieldset>

          <label className="wide-field">
            <span>file_name</span>
            <input
              aria-label="file_name"
              value={draft.fileName}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  fileName: event.target.value,
                }))
              }
              required
            />
            <small>Không chứa .txt và phải có hậu tố -{draft.queryType}.</small>
          </label>

          <label className="wide-field">
            <span>query_content</span>
            <textarea
              aria-label="query_content"
              value={draft.queryContent}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  queryContent: event.target.value,
                }))
              }
              required
            />
          </label>

          <label className="wide-field">
            <span>image_base64</span>
            <textarea
              aria-label="image_base64"
              value={draft.imageBase64}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  imageBase64: event.target.value,
                }))
              }
              placeholder="Chuỗi base64 thuần hoặc data:image/...;base64,..."
            />
            <small>
              Tùy chọn · JPEG, PNG hoặc WebP, tối đa 5 MiB sau giải mã.
            </small>
          </label>

          <div className="tester-fields">
            <label>
              <span>video_id</span>
              <input
                aria-label="video_id"
                value={draft.videoId}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    videoId: event.target.value,
                  }))
                }
                required
              />
            </label>
            <label>
              <span>img_id</span>
              <input
                aria-label="img_id"
                inputMode="numeric"
                value={draft.frames}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    frames: event.target.value,
                  }))
                }
                required
              />
              <small>
                {draft.queryType === "trake"
                  ? "Nhiều frame, phân cách bằng dấu phẩy."
                  : "Một frame ID."}
              </small>
            </label>
          </div>

          {draft.queryType === "qa" && (
            <label className="wide-field">
              <span>answer</span>
              <textarea
                aria-label="answer"
                value={draft.answer}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    answer: event.target.value,
                  }))
                }
                required
              />
            </label>
          )}

          {error && (
            <p className="tester-error" role="alert">
              {error}
            </p>
          )}
          <button className="button primary tester-submit" disabled={sending}>
            {sending ? "Đang gửi…" : "Gửi request"}
          </button>
        </form>

        <aside className="request-preview" aria-label="JSON request preview">
          <div className="preview-topline">
            <span>POST</span>
            <code>/api/v1/submissions</code>
          </div>
          <pre>{JSON.stringify(preview, null, 2)}</pre>
          {response && (
            <div className="tester-success" role="status">
              <b>201 Created</b>
              <span>
                Đã vào nhóm {response.file_name}, priority #{response.priority}.
              </span>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}
