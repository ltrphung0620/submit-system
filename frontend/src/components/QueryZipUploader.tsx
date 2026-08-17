import { useState, type ChangeEvent } from "react";

import { api } from "../api";

interface Props {
  onImported: (queryCount: number) => Promise<void> | void;
}

export function QueryZipUploader({ onImported }: Props) {
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (!file.name.toLocaleLowerCase().endsWith(".zip")) {
      setStatus("");
      setError("Chỉ nhận file .zip chứa các query .txt.");
      return;
    }

    setImporting(true);
    setError("");
    setStatus("");
    try {
      const imported = await api.importQueries(file);
      await onImported(imported.query_count);
      setStatus(`Đã nạp ${imported.query_count} query từ ${file.name}.`);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể nạp file ZIP.",
      );
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="query-import">
      <input
        id="query-zip-upload"
        className="visually-hidden"
        type="file"
        accept=".zip,application/zip,application/x-zip-compressed"
        onChange={upload}
        disabled={importing}
      />
      <label
        className="button secondary upload-trigger"
        htmlFor="query-zip-upload"
      >
        {importing ? "Đang nạp ZIP…" : "Nạp query ZIP"}
      </label>
      <p className="upload-help">Chọn file ZIP chứa các file query `.txt`.</p>
      {error && (
        <p className="upload-error" role="alert">
          {error}
        </p>
      )}
      {status && (
        <p className="upload-success" role="status">
          {status}
        </p>
      )}
    </div>
  );
}
