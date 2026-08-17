import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthGate } from "./AuthGate";

function response(
  ok: boolean,
  status: number,
  payload: Record<string, unknown>,
): Response {
  return {
    ok,
    status,
    json: async () => payload,
  } as Response;
}

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("AuthGate", () => {
  it("logs in with UI_SHARED_KEY, stores it, and logs out", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        response(false, 401, {
          error: {
            code: "AUTHENTICATION_REQUIRED",
            message: "Thiếu X-API-Key",
          },
        }),
      )
      .mockResolvedValueOnce(
        response(true, 200, {
          authenticated: true,
          client_type: "ui",
          actor: "UI",
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AuthGate>
        {(session, logout) => (
          <section>
            <span>Đã đăng nhập: {session.actor}</span>
            <button onClick={logout}>Đăng xuất thử</button>
          </section>
        )}
      </AuthGate>,
    );

    await screen.findByRole("heading", { name: "Đăng nhập hệ thống" });
    fireEvent.change(screen.getByLabelText("UI shared key"), {
      target: { value: "ui-shared-secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    await screen.findByText("Đã đăng nhập: UI");
    expect(window.localStorage.getItem("submission-api-key")).toBe(
      "ui-shared-secret",
    );
    const loginHeaders = fetchMock.mock.calls[1][1].headers as Record<
      string,
      string
    >;
    expect(loginHeaders["X-API-Key"]).toBe("ui-shared-secret");

    fireEvent.click(screen.getByRole("button", { name: "Đăng xuất thử" }));
    await screen.findByRole("heading", { name: "Đăng nhập hệ thống" });
    expect(window.localStorage.getItem("submission-api-key")).toBeNull();
  });

  it("rejects SALAMANDERS_KEY on the UI login", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        response(false, 401, {
          error: {
            code: "AUTHENTICATION_REQUIRED",
            message: "Thiếu X-API-Key",
          },
        }),
      )
      .mockResolvedValueOnce(
        response(true, 200, {
          authenticated: true,
          client_type: "salamanders",
          actor: "Salamanders",
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<AuthGate>{() => <span>Không được hiển thị</span>}</AuthGate>);

    await screen.findByRole("heading", { name: "Đăng nhập hệ thống" });
    fireEvent.change(screen.getByLabelText("UI shared key"), {
      target: { value: "salamanders-secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    await waitFor(() =>
      expect(
        screen.getByText("Key này không phải UI_SHARED_KEY."),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText("Không được hiển thị")).not.toBeInTheDocument();
    expect(window.localStorage.getItem("submission-api-key")).toBeNull();
  });
});
