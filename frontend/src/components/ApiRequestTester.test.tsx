import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiRequestTester } from "./ApiRequestTester";
import { buildSubmissionPayload } from "./submissionPayload";
import type { ResultCandidate } from "../types";

const response: ResultCandidate = {
  id: "result-1",
  query_id: "query-1",
  file_name: "synthetic-ui-test-qa",
  query_type: "qa",
  arrival_seq: 1,
  priority: 1,
  video_id: "L21_V001",
  img_id: 24834,
  answer: "Bình Định",
  submitter: "UI",
  note: null,
  created_at: "2026-07-24T00:00:00Z",
  updated_at: "2026-07-24T00:00:00Z",
  version: 1,
  structural_validation_status: "valid",
  official_validation_status: "unverified",
  image_url: null,
  image_mime_type: null,
};

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("buildSubmissionPayload", () => {
  it("builds a TRAKE array and rejects .txt file names", () => {
    expect(
      buildSubmissionPayload({
        queryType: "trake",
        fileName: "synthetic-route-trake",
        queryContent: "Theo dõi chiếc xe màu đỏ.",
        videoId: "L21_V001",
        frames: "1, 2, 3",
        answer: "",
        submitter: "Tester",
        imageBase64: "",
      }),
    ).toEqual({
      file_name: "synthetic-route-trake",
      query_content: "Theo dõi chiếc xe màu đỏ.",
      img_id: [1, 2, 3],
      video_id: "L21_V001",
      submitter: "Tester",
    });
    expect(() =>
      buildSubmissionPayload({
        queryType: "kis",
        fileName: "synthetic-route-kis.txt",
        queryContent: "Tìm một người bước vào cửa hàng.",
        videoId: "L21_V001",
        frames: "1",
        answer: "",
        submitter: "Tester",
        imageBase64: "",
      }),
    ).toThrow("không được chứa đuôi .txt");
  });
});

describe("ApiRequestTester", () => {
  it("switches request shape and submits through the public endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => response,
    } as Response);
    vi.stubGlobal("fetch", fetchMock);
    window.localStorage.setItem("submission-api-key", "ui-shared-secret");
    const onSubmitted = vi.fn();

    render(<ApiRequestTester onSubmitted={onSubmitted} />);
    fireEvent.click(screen.getByRole("button", { name: "QA" }));

    const fileNameInput = screen.getByLabelText("file_name");
    const queryContentInput = screen.getByLabelText("query_content");
    expect(fileNameInput).toHaveValue("synthetic-ui-test-qa");
    expect(queryContentInput).toHaveValue(
      "Tìm khoảnh khắc một người bước vào cửa hàng.",
    );
    expect(fileNameInput.closest("label")?.nextElementSibling).toBe(
      queryContentInput.closest("label"),
    );
    expect(screen.getByLabelText("answer")).toBeInTheDocument();
    const imageBase64 = "data:image/png;base64,c3ludGhldGlj";
    fireEvent.change(screen.getByLabelText("image_base64"), {
      target: { value: `  ${imageBase64}  ` },
    });
    const preview = screen.getByLabelText("JSON request preview");
    expect(preview).toHaveTextContent(
      `<base64 đã ẩn: ${imageBase64.length} ký tự>`,
    );
    expect(preview).not.toHaveTextContent(imageBase64);
    fireEvent.click(screen.getByRole("button", { name: "Gửi request" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/submissions");
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(String(init.body))).toEqual({
      file_name: "synthetic-ui-test-qa",
      query_content: "Tìm khoảnh khắc một người bước vào cửa hàng.",
      img_id: 24834,
      video_id: "L21_V001",
      answer: "Bình Định",
      submitter: "UI",
      image_base64: imageBase64,
    });
    expect((init.headers as Record<string, string>)["X-API-Key"]).toBe(
      "ui-shared-secret",
    );
    await waitFor(() => expect(onSubmitted).toHaveBeenCalledWith(response));
    expect(screen.getByText("201 Created")).toBeInTheDocument();
    expect(screen.getByText(/priority #1/)).toBeInTheDocument();
  });
});
