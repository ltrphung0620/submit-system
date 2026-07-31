export type QueryType = "kis" | "qa" | "trake" | "unknown";
export type SubmissionQueryType = Exclude<QueryType, "unknown">;

export interface SubmissionPayload {
  file_name: string;
  query_content: string;
  img_id: number | number[];
  video_id: string;
  submitter: string;
  answer?: string;
  image_base64?: string;
}

export interface ResultCandidate {
  id: string;
  query_id: string;
  file_name: string;
  query_type: QueryType;
  arrival_seq: number;
  priority: number;
  video_id: string;
  img_id: number | number[];
  answer: string | null;
  submitter: string;
  note: string | null;
  created_at: string;
  updated_at: string;
  version: number;
  structural_validation_status: string;
  official_validation_status: string;
  image_url: string | null;
  image_mime_type: string | null;
}

export interface QueryRow {
  id: string;
  query_set_id: string;
  file_name: string;
  query_type: QueryType;
  content: string;
  display_order: number;
  source_path: string;
  results: ResultCandidate[];
}

export interface ExportStatus {
  preview_enabled: boolean;
  preview_label: string;
  official_enabled: boolean;
  official_status: string;
  blockers: string[];
}

export interface RealtimeEvent {
  schema_version: number;
  event: "created" | "updated" | "deleted" | "query_set_imported";
  occurred_at: string;
  data:
    | ResultCandidate
    | { id: string; query_id: string }
    | Record<string, unknown>;
}
