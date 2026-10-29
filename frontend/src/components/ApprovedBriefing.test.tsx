import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApprovedBriefing } from "./ApprovedBriefing";

describe("ApprovedBriefing", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders approved content with site typography and removes embedded code", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            "<html><body><main><h1>Approved record</h1><p>Verified exposure.</p>" +
              "<script>throw new Error('must not run')</script></main></body></html>",
            { status: 200 },
          ),
        ),
    );

    render(<ApprovedBriefing path="/briefings/test.html" />);

    expect(
      await screen.findByRole("heading", { name: "Approved record" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Verified exposure.")).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    expect(document.querySelector("article.approved-briefing")).not.toBeNull();
  });
});
