import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { QueryZipUploader } from "./QueryZipUploader";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("QueryZipUploader", () => {
  it("uploads a ZIP and refreshes the query list", async () => {
    const importQueries = vi
      .spyOn(api, "importQueries")
      .mockResolvedValue({ query_count: 2 });
    const onImported = vi.fn().mockResolvedValue(undefined);
    render(<QueryZipUploader onImported={onImported} />);

    const file = new File(["zip-content"], "query-p1-groupA.zip", {
      type: "application/zip",
    });
    fireEvent.change(screen.getByLabelText("Nạp query ZIP"), {
      target: { files: [file] },
    });

    await waitFor(() => expect(importQueries).toHaveBeenCalledWith(file));
    expect(onImported).toHaveBeenCalledWith(2);
    expect(screen.getByRole("status")).toHaveTextContent("Đã nạp 2 query");
  });

  it("rejects a non-ZIP file before sending it", () => {
    const importQueries = vi.spyOn(api, "importQueries");
    render(<QueryZipUploader onImported={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Nạp query ZIP"), {
      target: { files: [new File(["text"], "query.txt")] },
    });

    expect(importQueries).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Chỉ nhận file .zip");
  });
});
