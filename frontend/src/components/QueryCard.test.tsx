import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { QueryCard } from "./QueryCard";
import type { QueryRow } from "../types";

describe("QueryCard", () => {
  it("shows answer only for QA and keeps the requested actions", () => {
    const query: QueryRow = {
      id: "q1",
      query_set_id: "s1",
      file_name: "query-1-qa",
      query_type: "qa",
      content: "<img src=x onerror=alert(1)>",
      display_order: 1,
      source_path: "query-1-qa.txt",
      results: [
        {
          id: "r1",
          query_id: "q1",
          file_name: "query-1-qa",
          query_type: "qa",
          arrival_seq: 1,
          priority: 1,
          video_id: "L21_V001",
          img_id: 24834,
          answer: "Bình Định",
          submitter: "Định",
          note: null,
          created_at: "2026-07-24T00:00:00Z",
          updated_at: "2026-07-24T00:00:00Z",
          version: 1,
          structural_validation_status: "valid",
          official_validation_status: "unverified",
          image_url: "/api/v1/images/image-1",
          image_mime_type: "image/png",
        },
      ],
    };
    const onExport = vi.fn();
    const onSwap = vi.fn();
    const onReorder = vi.fn();
    const { container, rerender } = render(
      <QueryCard
        index={1}
        query={query}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onExport={onExport}
        exporting={false}
        onSwap={onSwap}
        onReorder={onReorder}
        swappingResultIds={[]}
      />,
    );
    const image = screen.getByRole("img", {
      name: "Ảnh của query-1-qa, priority 1",
    });
    expect(image).toHaveAttribute("src", "/api/v1/images/image-1");
    expect(
      screen.getByRole("link", {
        name: "Mở ảnh của query-1-qa, priority 1",
      }),
    ).toHaveAttribute("href", "/api/v1/images/image-1");
    expect(container.querySelector('img[src="x"]')).toBeNull();
    expect(screen.getByText("video_id")).toBeInTheDocument();
    expect(screen.getByText("img_id")).toBeInTheDocument();
    expect(screen.getByText("answer")).toBeInTheDocument();
    expect(screen.getByText("submitter")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sửa" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Xóa" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Xuất CSV" }));
    expect(onExport).toHaveBeenCalledWith(query);
    expect(screen.getByText("Bình Định")).toBeInTheDocument();
    expect(screen.queryByText("Nhận lúc")).not.toBeInTheDocument();
    expect(screen.queryByText(/Hợp lệ/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Đến #/)).not.toBeInTheDocument();
    expect(
      screen.getByText("<img src=x onerror=alert(1)>"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(
        "Nhóm được tạo tự động khi public API nhận request đầu tiên.",
      ),
    ).not.toBeInTheDocument();

    const kisQuery: QueryRow = {
      ...query,
      query_type: "kis",
      results: [
        ...query.results.map((result) => ({
          ...result,
          query_type: "kis" as const,
          answer: null,
        })),
        {
          ...query.results[0],
          id: "r2",
          query_type: "kis",
          arrival_seq: 2,
          priority: 2,
          img_id: 24835,
          answer: null,
          image_url: null,
          image_mime_type: null,
        },
      ],
    };
    rerender(
      <QueryCard
        index={1}
        query={kisQuery}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onExport={onExport}
        exporting={false}
        onSwap={onSwap}
        onReorder={onReorder}
        swappingResultIds={[]}
      />,
    );
    expect(screen.queryByText("answer")).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Đưa priority 2 lên trước" }),
    );
    expect(onSwap).toHaveBeenCalledWith(
      kisQuery.results[1],
      kisQuery.results[0],
    );
    const firstCard = screen.getByText("Priority #1").closest(".candidate");
    const secondCard = screen.getByText("Priority #2").closest(".candidate");
    const dataTransfer = {
      effectAllowed: "",
      dropEffect: "",
      setData: vi.fn(),
    };
    fireEvent.dragStart(firstCard as HTMLElement, { dataTransfer });
    fireEvent.dragOver(secondCard as HTMLElement, { dataTransfer });
    fireEvent.drop(secondCard as HTMLElement, { dataTransfer });
    expect(onReorder).toHaveBeenCalledWith(kisQuery, [
      kisQuery.results[1],
      kisQuery.results[0],
    ]);
  });
});
