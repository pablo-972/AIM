import { AlertTriangle, CheckCircle2, Circle, Loader2 } from "lucide-react";
import type { AnalysisStatusPayload, PhaseState } from "../../types";

const phaseLabels: Record<string, string> = {
  static: "Static",
  static_inference: "Static Inference",
  dynamic: "Dynamic",
  dynamic_inference: "Dynamic Inference",
  enrichment: "Enrichment",
  reverse_info: "Reverse Info",
  reverse_agent: "Reverse Agent",
  report: "Report",
};

type AnalysisStatusProps = {
  status: AnalysisStatusPayload;
};

function AnalysisStatus({ status }: AnalysisStatusProps) {
  return (
    <section className="rounded-md border border-line bg-panel p-5">
      <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm uppercase text-muted">Analysis</p>
          <p className="break-all text-lg font-semibold">{status.analysis_id}</p>
        </div>
        <StatusBadge state={status.status} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Object.entries(status.phases).map(([phase, state]) => (
          <div
            key={phase}
            className="flex min-h-16 items-center justify-between rounded border border-line bg-panelSoft px-4 py-3"
          >
            <div>
              <p className="text-sm font-medium">{phaseLabels[phase] ?? phase}</p>
              <p className="text-xs uppercase text-muted">{state}</p>
            </div>
            <PhaseIcon state={state} />
          </div>
        ))}
      </div>

      {status.error && (
        <div className="mt-4 rounded border border-danger/50 bg-red-950/30 p-3 text-sm text-red-100">
          {status.error}
        </div>
      )}
    </section>
  );
}

function StatusBadge({ state }: { state: AnalysisStatusPayload["status"] }) {
  const classes =
    state === "completed"
      ? "border-emerald-500/40 bg-emerald-950/50 text-emerald-200"
      : state === "failed"
        ? "border-danger/50 bg-red-950/50 text-red-100"
        : "border-accent/40 bg-teal-950/40 text-teal-100";

  return (
    <span className={`w-fit rounded border px-3 py-1 text-sm font-medium ${classes}`}>
      {state}
    </span>
  );
}

function PhaseIcon({ state }: { state: PhaseState }) {
  if (state === "completed") {
    return <CheckCircle2 className="h-5 w-5 text-emerald-400" aria-hidden="true" />;
  }
  if (state === "failed") {
    return <AlertTriangle className="h-5 w-5 text-danger" aria-hidden="true" />;
  }
  if (state === "running") {
    return <Loader2 className="h-5 w-5 animate-spin text-accent" aria-hidden="true" />;
  }
  return <Circle className="h-5 w-5 text-muted" aria-hidden="true" />;
}

export default AnalysisStatus;
