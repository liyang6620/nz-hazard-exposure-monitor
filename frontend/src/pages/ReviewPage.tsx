import { useEffect, useState } from "react";

type Preview = { title: string; action: "approve" | "reject" };
type ReviewState =
  | { kind: "waking"; attempts: number }
  | { kind: "ready"; preview: Preview }
  | { kind: "submitting"; preview: Preview }
  | { kind: "done"; status: string }
  | { kind: "unavailable"; message: string };

const apiBase =
  import.meta.env.VITE_REVIEW_API_BASE_URL ||
  "http://127.0.0.1:8000/review-briefing";

export default function ReviewPage() {
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
  const [state, setState] = useState<ReviewState>(() =>
    token
      ? { kind: "waking", attempts: 0 }
      : { kind: "unavailable", message: "This review link is missing." },
  );

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    const preview = async () => {
      for (let attempt = 1; attempt <= 5; attempt++) {
        if (controller.signal.aborted) return;
        setState({ kind: "waking", attempts: attempt });
        try {
          const response = await fetch(apiBase, {
            method: "GET",
            headers: { Accept: "application/json", "X-Review-Token": token },
            credentials: "omit",
            referrerPolicy: "no-referrer",
            signal: AbortSignal.any([
              controller.signal,
              AbortSignal.timeout(15_000),
            ]),
          });
          if (response.status === 400 || response.status === 404) {
            setState({
              kind: "unavailable",
              message: "This review link is unavailable.",
            });
            return;
          }
          if (response.ok) {
            const data = (await response.json()) as Preview;
            if (data.action !== "approve" && data.action !== "reject") {
              throw new Error("Invalid preview response");
            }
            setState({ kind: "ready", preview: data });
            return;
          }
        } catch (error) {
          if (controller.signal.aborted) return;
          if (error instanceof SyntaxError) {
            setState({
              kind: "unavailable",
              message: "Review could not be loaded.",
            });
            return;
          }
        }
        if (attempt < 5) {
          await new Promise((resolve) => setTimeout(resolve, attempt * 1500));
        }
      }
      if (!controller.signal.aborted) {
        setState({
          kind: "unavailable",
          message:
            "The review service is unavailable. Please refresh the page shortly.",
        });
      }
    };
    void preview();
    return () => controller.abort();
  }, [token]);

  const decide = async (preview: Preview) => {
    if (!token) return;
    setState({ kind: "submitting", preview });
    try {
      const response = await fetch(apiBase, {
        method: "POST",
        headers: { Accept: "application/json", "X-Review-Token": token },
        credentials: "omit",
        referrerPolicy: "no-referrer",
      });
      if (response.ok) {
        const data = (await response.json()) as { status: string };
        setState({ kind: "done", status: data.status });
      } else if (response.status === 400 || response.status === 404) {
        setState({
          kind: "unavailable",
          message: "This review link is unavailable or already used.",
        });
      } else {
        setState({
          kind: "unavailable",
          message:
            "The decision could not be confirmed. Check the briefing page before trying again.",
        });
      }
    } catch {
      setState({
        kind: "unavailable",
        message:
          "The decision could not be confirmed. Check the briefing page before trying again.",
      });
    }
  };

  return (
    <main className="review-page">
      <div className="review-heading">NZ Hazard Exposure Monitor</div>
      {state.kind === "waking" && (
        <section role="status" aria-live="polite">
          <h1>Waking the review service</h1>
          <p>Connecting to the review service. This can take a moment.</p>
        </section>
      )}
      {(state.kind === "ready" || state.kind === "submitting") && (
        <section>
          <h1>{state.preview.title}</h1>
          <p>Confirm {state.preview.action} for this briefing.</p>
          <button
            className="review-confirm"
            type="button"
            disabled={state.kind === "submitting"}
            onClick={() => void decide(state.preview)}
          >
            {state.kind === "submitting"
              ? "Submitting decision…"
              : `Confirm ${state.preview.action}`}
          </button>
        </section>
      )}
      {state.kind === "done" && <h1>Briefing {state.status}</h1>}
      {state.kind === "unavailable" && (
        <section role="alert">
          <h1>Review unavailable</h1>
          <p>{state.message}</p>
        </section>
      )}
    </main>
  );
}
