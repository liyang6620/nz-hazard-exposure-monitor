import { useEffect, useState } from "react";

import { ErrorState, LoadingState } from "./AsyncState";

export function ApprovedBriefing({ path }: { path: string }) {
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(path, { signal: controller.signal, cache: "no-cache" })
      .then((response) => {
        if (!response.ok)
          throw new Error(`Briefing request failed (${response.status})`);
        return response.text();
      })
      .then((source) => setHtml(extractApprovedContent(source)))
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError")
          return;
        setError(
          reason instanceof Error ? reason.message : "Briefing unavailable",
        );
      });
    return () => controller.abort();
  }, [path]);

  if (error) return <ErrorState message={error} />;
  if (html === null) return <LoadingState label="Loading approved briefing" />;
  return (
    <article
      className="approved-briefing"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function extractApprovedContent(source: string): string {
  const document = new DOMParser().parseFromString(source, "text/html");
  document
    .querySelectorAll("script, style, link, iframe, object, embed")
    .forEach((element) => element.remove());
  document.body.querySelectorAll("*").forEach((element) => {
    for (const attribute of Array.from(element.attributes)) {
      if (attribute.name.toLowerCase().startsWith("on"))
        element.removeAttribute(attribute.name);
    }
  });
  return document.body.innerHTML;
}
