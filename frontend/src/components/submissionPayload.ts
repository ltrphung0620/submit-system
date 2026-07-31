import type { SubmissionPayload, SubmissionQueryType } from "../types";

export interface SubmissionDraft {
  queryType: SubmissionQueryType;
  fileName: string;
  queryContent: string;
  videoId: string;
  frames: string;
  answer: string;
  submitter: string;
  imageBase64: string;
}

function parseFrames(value: string): number[] {
  const parts = value.split(",").map((part) => part.trim());
  if (!parts.length || parts.some((part) => !/^\d+$/.test(part))) {
    throw new Error(
      "img_id chỉ nhận số nguyên không âm; TRAKE ngăn cách bằng dấu phẩy.",
    );
  }
  return parts.map(Number);
}

export function buildSubmissionPayload(
  draft: SubmissionDraft,
): SubmissionPayload {
  const fileName = draft.fileName.trim();
  if (!fileName || fileName.toLocaleLowerCase().endsWith(".txt")) {
    throw new Error("file_name là bắt buộc và không được chứa đuôi .txt.");
  }
  if (!fileName.toLocaleLowerCase().endsWith(`-${draft.queryType}`)) {
    throw new Error(`file_name phải kết thúc bằng -${draft.queryType}.`);
  }
  const queryContent = draft.queryContent.trim();
  if (!queryContent) throw new Error("query_content là bắt buộc.");
  if (!draft.videoId.trim()) throw new Error("video_id là bắt buộc.");
  if (!draft.submitter.trim()) throw new Error("submitter là bắt buộc.");

  const frames = parseFrames(draft.frames);
  if (draft.queryType !== "trake" && frames.length !== 1) {
    throw new Error("KIS và QA chỉ nhận đúng một frame trong img_id.");
  }
  if (draft.queryType === "qa" && !draft.answer.trim()) {
    throw new Error("QA yêu cầu answer.");
  }

  const payload: SubmissionPayload = {
    file_name: fileName,
    query_content: queryContent,
    img_id: draft.queryType === "trake" ? frames : frames[0],
    video_id: draft.videoId.trim(),
    submitter: draft.submitter.trim(),
  };
  if (draft.queryType === "qa") payload.answer = draft.answer.trim();
  const imageBase64 = draft.imageBase64.trim();
  if (imageBase64) payload.image_base64 = imageBase64;
  return payload;
}
