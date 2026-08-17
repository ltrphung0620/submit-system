import type {
  AuthSession,
  ExportStatus,
  QueryRow,
  ResultCandidate,
  SubmissionPayload,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
const API_KEY_STORAGE_KEY = "submission-api-key";

export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export function storedUiApiKey(): string | null {
  return window.localStorage.getItem(API_KEY_STORAGE_KEY);
}

export function saveUiApiKey(key: string): void {
  window.localStorage.setItem(API_KEY_STORAGE_KEY, key);
}

export function clearUiApiKey(): void {
  window.localStorage.removeItem(API_KEY_STORAGE_KEY);
}

function authHeaders(apiKey?: string | null): Record<string, string> {
  const key = apiKey === undefined ? storedUiApiKey() : apiKey;
  return key ? { "X-API-Key": key } : {};
}

async function request<T>(
  path: string,
  init?: RequestInit,
  apiKey?: string | null,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...authHeaders(apiKey),
      ...(init?.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      error?: { message?: string; code?: string };
    } | null;
    throw new ApiClientError(
      payload?.error?.message ?? `Request failed (${response.status})`,
      payload?.error?.code ?? "HTTP_ERROR",
      response.status,
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function downloadFile(path: string, filename: string): Promise<void> {
  const response = await fetch(path, { headers: authHeaders() });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      error?: { message?: string; code?: string };
    } | null;
    throw new ApiClientError(
      payload?.error?.message ?? `Request failed (${response.status})`,
      payload?.error?.code ?? "HTTP_ERROR",
      response.status,
    );
  }
  const objectUrl = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
}

function csvDownloadFilename(fileName: string): string {
  const sanitized = fileName
    .replace(/[^A-Za-z0-9._-]/g, "_")
    .replace(/^[._]+|[._]+$/g, "");
  return `${sanitized || "submission"}.csv`;
}

export const api = {
  authSession: (apiKey?: string | null) =>
    request<AuthSession>("/auth/me", undefined, apiKey),
  listQueries: () => request<QueryRow[]>("/queries"),
  deleteQuery: (queryId: string) =>
    request<void>(`/queries/${encodeURIComponent(queryId)}`, {
      method: "DELETE",
    }),
  deleteAllQueries: () => request<void>("/queries", { method: "DELETE" }),
  importQueries: (file: File) => {
    const data = new FormData();
    data.append("upload", file);
    return request<{ query_count: number }>("/query-sets/import", {
      method: "POST",
      body: data,
    });
  },
  createResult: (body: Record<string, unknown>) =>
    request<ResultCandidate>("/results", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  createSubmission: (body: SubmissionPayload) =>
    request<ResultCandidate>("/submissions", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  duplicateResult: (resultId: string) =>
    request<ResultCandidate>(
      `/results/${encodeURIComponent(resultId)}/duplicate`,
      {
        method: "POST",
      },
    ),
  updateResult: (id: string, body: Record<string, unknown>) =>
    request<ResultCandidate>(`/results/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteResult: (result: ResultCandidate) =>
    request<void>(`/results/${result.id}?expected_version=${result.version}`, {
      method: "DELETE",
    }),
  swapPriorities: (first: ResultCandidate, second: ResultCandidate) =>
    request<ResultCandidate[]>("/results/priority/swap", {
      method: "POST",
      body: JSON.stringify({
        first_result_id: first.id,
        second_result_id: second.id,
        expected_first_version: first.version,
        expected_second_version: second.version,
      }),
    }),
  reorderPriorities: (query: QueryRow, orderedResults: ResultCandidate[]) =>
    request<ResultCandidate[]>("/results/priority/reorder", {
      method: "POST",
      body: JSON.stringify({
        query_id: query.id,
        ordered_result_ids: orderedResults.map((result) => result.id),
        expected_versions: Object.fromEntries(
          query.results.map((result) => [result.id, result.version]),
        ),
      }),
    }),
  exportStatus: () => request<ExportStatus>("/exports/status"),
  validateExport: () => request<Record<string, unknown>>("/exports/validate"),
  downloadSubmissionZip: async () => {
    const artifact = await request<{ download_url: string; label: string }>(
      "/exports/preview",
      {
        method: "POST",
      },
    );
    await downloadFile(artifact.download_url, "submission.zip");
    return artifact;
  },
  downloadQueryCsv: (queryId: string, fileName: string) =>
    downloadFile(
      `${API_BASE}/exports/queries/${encodeURIComponent(queryId)}.csv`,
      csvDownloadFilename(fileName),
    ),
  historyDownloadUrl: () => `${API_BASE}/exports/history.csv`,
};

export function websocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${API_BASE}/ws`;
}
