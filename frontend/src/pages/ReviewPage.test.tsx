import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewPage from "./ReviewPage";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

test("GET preview never decides; a click sends exactly one POST", async () => {
  window.history.replaceState({}, "", "/review#token=test-token");
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ title: "M7.8 Kaikōura", action: "approve" }),
    })
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ status: "approved" }),
    });
  vi.stubGlobal("fetch", fetchMock);
  render(<ReviewPage />);
  await screen.findByRole("button", { name: "Confirm approve" });
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls[0][1].method).toBe("GET");
  expect(fetchMock.mock.calls[0][0]).not.toContain("test-token");
  expect(fetchMock.mock.calls[0][1].headers["X-Review-Token"]).toBe(
    "test-token",
  );
  fireEvent.click(screen.getByRole("button", { name: "Confirm approve" }));
  await screen.findByRole("heading", { name: "Briefing approved" });
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(fetchMock.mock.calls[1][1].method).toBe("POST");
  expect(fetchMock.mock.calls[1][0]).not.toContain("test-token");
});

test("invalid link never offers a decision", async () => {
  window.history.replaceState({}, "", "/review#token=bad-token");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 400 }));
  render(<ReviewPage />);
  await waitFor(() =>
    expect(screen.getByRole("alert")).toHaveTextContent("unavailable"),
  );
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});
