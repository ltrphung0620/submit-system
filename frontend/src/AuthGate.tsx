import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { api, clearUiApiKey, saveUiApiKey, storedUiApiKey } from "./api";
import type { AuthSession } from "./types";

interface Props {
  children: (session: AuthSession, logout: () => void) => ReactNode;
}

type GateState =
  | { status: "checking" }
  | { status: "signed_out"; message: string }
  | { status: "signed_in"; session: AuthSession };

export function AuthGate({ children }: Props) {
  const [state, setState] = useState<GateState>({ status: "checking" });
  const [apiKey, setApiKey] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      const savedKey = storedUiApiKey();
      try {
        const session = await api.authSession(savedKey);
        if (!active) return;
        if (session.client_type === "anonymous") {
          setState({ status: "signed_in", session });
          return;
        }
        if (session.client_type === "ui" && savedKey) {
          setState({ status: "signed_in", session });
          return;
        }
        clearUiApiKey();
        setState({
          status: "signed_out",
          message: "Key đã lưu không phải UI_SHARED_KEY.",
        });
      } catch {
        if (!active) return;
        clearUiApiKey();
        setState({
          status: "signed_out",
          message: savedKey ? "UI_SHARED_KEY đã lưu không còn hợp lệ." : "",
        });
      }
    }

    void restoreSession();
    return () => {
      active = false;
    };
  }, []);

  async function login(event: FormEvent) {
    event.preventDefault();
    const key = apiKey.trim();
    if (!key) {
      setState({
        status: "signed_out",
        message: "Hãy nhập UI_SHARED_KEY.",
      });
      return;
    }

    setSubmitting(true);
    try {
      const session = await api.authSession(key);
      if (session.client_type !== "ui") {
        throw new Error("Key này không phải UI_SHARED_KEY.");
      }
      saveUiApiKey(key);
      setApiKey("");
      setState({ status: "signed_in", session });
    } catch (reason) {
      clearUiApiKey();
      setState({
        status: "signed_out",
        message:
          reason instanceof Error
            ? reason.message
            : "Không thể xác thực UI_SHARED_KEY.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  function logout() {
    clearUiApiKey();
    setApiKey("");
    setState({ status: "signed_out", message: "" });
  }

  if (state.status === "checking") {
    return (
      <main className="login-page" aria-busy="true">
        <section className="login-card">
          <p className="eyebrow">Submission System</p>
          <h1>Đang kiểm tra phiên đăng nhập…</h1>
        </section>
      </main>
    );
  }

  if (state.status === "signed_out") {
    return (
      <main className="login-page">
        <section className="login-card" aria-labelledby="login-title">
          <span className="login-mark">AIC</span>
          <p className="eyebrow">Submission System</p>
          <h1 id="login-title">Đăng nhập hệ thống</h1>
          <p className="login-copy">
            Nhập UI_SHARED_KEY do quản trị viên cấp. Key chỉ được lưu trên trình
            duyệt này và tự động gửi trong header X-API-Key.
          </p>
          <form className="login-form" onSubmit={login}>
            <label>
              <span>UI shared key</span>
              <input
                type="password"
                name="api-key"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                autoComplete="current-password"
                autoFocus
                spellCheck={false}
                required
              />
            </label>
            {state.message && (
              <p className="login-error" role="alert">
                {state.message}
              </p>
            )}
            <button
              className="button primary large"
              type="submit"
              disabled={submitting}
            >
              {submitting ? "Đang xác thực…" : "Đăng nhập"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return <>{children(state.session, logout)}</>;
}
