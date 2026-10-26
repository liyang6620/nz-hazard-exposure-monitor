import { AlertTriangle, LoaderCircle, RotateCcw } from "lucide-react";

export function LoadingState({
  label = "Loading exposure data",
}: {
  label?: string;
}) {
  return (
    <div className="state-panel" role="status">
      <LoaderCircle className="spin" size={22} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="state-panel error" role="alert">
      <AlertTriangle size={22} aria-hidden="true" />
      <div>
        <strong>Data could not be loaded</strong>
        <p>{message}</p>
      </div>
      {retry ? (
        <button className="button secondary" type="button" onClick={retry}>
          <RotateCcw size={16} />
          Retry
        </button>
      ) : null}
    </div>
  );
}
