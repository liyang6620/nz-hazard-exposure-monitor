import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { useLocation } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { SiteDataProvider } from "./app/SiteDataContext";
import { LoadingState } from "./components/AsyncState";

const HomePage = lazy(() => import("./pages/HomePage"));
const EventDetailPage = lazy(() => import("./pages/EventDetailPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const MethodologyPage = lazy(() => import("./pages/MethodologyPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));
const WorkbenchPage = lazy(() => import("./pages/WorkbenchPage"));
const ReviewPage = lazy(() => import("./pages/ReviewPage"));

export default function App() {
  const location = useLocation();
  if (location.pathname === "/review") {
    return (
      <Suspense fallback={<div className="review-page">Loading review…</div>}>
        <ReviewPage />
      </Suspense>
    );
  }
  return (
    <SiteDataProvider>
      <AppShell>
        <Suspense
          fallback={
            <div className="page-container">
              <LoadingState />
            </div>
          }
        >
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/events/:eventId" element={<EventDetailPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/method" element={<MethodologyPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/workbench" element={<WorkbenchPage />} />
            <Route
              path="*"
              element={
                <div className="page-container not-found">
                  <h1>Page not found</h1>
                  <LinkHome />
                </div>
              }
            />
          </Routes>
        </Suspense>
      </AppShell>
    </SiteDataProvider>
  );
}

function LinkHome() {
  return (
    <a className="button primary" href="/">
      Return to overview
    </a>
  );
}
