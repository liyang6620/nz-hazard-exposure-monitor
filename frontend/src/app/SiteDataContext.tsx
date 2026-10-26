import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { loadSiteData } from "../data/client";
import type { SiteData } from "../data/types";

interface SiteDataState {
  data: SiteData | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

const SiteDataContext = createContext<SiteDataState | null>(null);

export function SiteDataProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<SiteData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    loadSiteData(controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError")
          return;
        setError(
          reason instanceof Error
            ? reason.message
            : "Website data is unavailable",
        );
      });
    return () => controller.abort();
  }, [reloadKey]);

  const value = useMemo(
    () => ({
      data,
      error,
      loading: data === null && error === null,
      reload: () => {
        setData(null);
        setError(null);
        setReloadKey((n) => n + 1);
      },
    }),
    [data, error],
  );

  return (
    <SiteDataContext.Provider value={value}>
      {children}
    </SiteDataContext.Provider>
  );
}

export function useSiteData(): SiteDataState {
  const context = useContext(SiteDataContext);
  if (!context)
    throw new Error("useSiteData must be used within SiteDataProvider");
  return context;
}
