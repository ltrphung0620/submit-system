import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ExportWarningsDialog } from "./ExportWarningsDialog";

describe("ExportWarningsDialog", () => {
  it("shows a warning table and bullet-points multiple notes", () => {
    const onContinue = vi.fn();
    render(
      <ExportWarningsDialog
        warnings={[
          { fileName: "query-empty-kis", notes: ["Chưa có đáp án"] },
          {
            fileName: "query-noted-qa",
            notes: ["Ghi chú 1", "Ghi chú 2"],
          },
        ]}
        canContinue
        onClose={vi.fn()}
        onContinue={onContinue}
      />,
    );

    expect(screen.getByRole("columnheader", { name: "Tên query" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Lưu ý" })).toBeInTheDocument();
    expect(screen.getByText("Chưa có đáp án")).toBeInTheDocument();
    expect(screen.getByRole("list")).toHaveTextContent("Ghi chú 1");
    expect(screen.getByRole("list")).toHaveTextContent("Ghi chú 2");
    fireEvent.click(screen.getByRole("button", { name: "Vẫn xuất ZIP" }));
    expect(onContinue).toHaveBeenCalledOnce();
  });
});
