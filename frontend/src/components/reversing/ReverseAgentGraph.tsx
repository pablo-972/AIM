import { useMemo, useState } from "react";
import { GitBranch, Network } from "lucide-react";
import type { AgentTrace, JsonArtifact, TraceStep } from "../../types";
import JsonExpandable from "../common/JsonExpandable";

type ReverseAgentGraphProps = {
  trace: JsonArtifact<AgentTrace> | null;
};

function ReverseAgentGraph({ trace }: ReverseAgentGraphProps) {
  const steps = trace?.data?.steps ?? [];
  const findings = trace?.data?.findings ?? [];
  const [selectedStep, setSelectedStep] = useState<number | null>(null);
  const selected = useMemo(
    () => steps.find((step) => step.step === selectedStep) ?? steps[0],
    [selectedStep, steps],
  );
  const visibleSteps = steps.slice(0, 24);

  if (!trace?.available || !trace.data) {
    return <EmptyPanel text="Reverse agent trace is not available yet." />;
  }

  return (
    <section className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
      <div className="min-w-0 space-y-5">
        <header className="min-w-0 overflow-hidden rounded-md border border-line bg-panel p-5">
          <div className="flex items-center gap-3">
            <Network className="h-5 w-5 text-accent" aria-hidden="true" />
            <div>
              <h2 className="text-lg font-semibold">Reverse Agent</h2>
              <p className="text-sm text-muted">{trace.data.status ?? "running"}</p>
            </div>
          </div>
        </header>

        <section className="min-w-0 overflow-hidden rounded-md border border-line bg-panel p-5">
          <h3 className="mb-4 font-semibold">Execution Nodes</h3>
          {visibleSteps.length ? (
            <div className="grid gap-3">
              {visibleSteps.map((step, index) => (
                <NodeButton
                  key={step.step}
                  step={step}
                  active={selected?.step === step.step}
                  hasNext={index < visibleSteps.length - 1}
                  onClick={() => setSelectedStep(step.step)}
                />
              ))}
              {steps.length > visibleSteps.length && (
                <p className="text-sm text-muted">
                  Showing first {visibleSteps.length} of {steps.length} steps.
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted">No reverse agent steps recorded yet.</p>
          )}
        </section>

        <section className="min-w-0 overflow-hidden rounded-md border border-line bg-panel p-5">
          <h3 className="mb-4 font-semibold">Findings</h3>
          {findings.length ? (
            <div className="grid gap-3">
              {findings.map((finding, index) => (
                <JsonExpandable
                  key={index}
                  data={finding}
                  label={`Finding ${index + 1}`}
                  defaultOpen={index === 0}
                />
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">No reverse findings recorded.</p>
          )}
        </section>
      </div>

      <aside className="min-w-0 overflow-hidden rounded-md border border-line bg-panel p-5 lg:sticky lg:top-5 lg:self-start">
        <h3 className="mb-4 font-semibold">Node Detail</h3>
        {selected ? (
          <div className="grid gap-3">
            <JsonExpandable data={selected.input ?? null} label="Input" defaultOpen />
            <JsonExpandable data={selected.decision ?? null} label="Decision" defaultOpen />
            <JsonExpandable data={selected.tool ?? null} label="Tool" />
            <JsonExpandable data={selected.finding ?? null} label="Finding" />
            {selected.error && (
              <div className="rounded border border-danger/40 bg-red-950/30 p-3 text-sm text-red-100">
                {selected.error}
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted">Select a node to inspect details.</p>
        )}
      </aside>
    </section>
  );
}

function NodeButton({
  step,
  active,
  hasNext,
  onClick,
}: {
  step: TraceStep;
  active: boolean;
  hasNext: boolean;
  onClick: () => void;
}) {
  return (
    <div className="min-w-0 overflow-hidden">
      <button
        type="button"
        onClick={onClick}
        className={`flex w-full min-w-0 items-center justify-between gap-4 rounded border p-4 text-left transition ${
          active
            ? "border-accent bg-teal-950/30"
            : "border-line bg-panelSoft hover:border-accent/70"
        }`}
      >
        <div className="min-w-0 overflow-hidden">
          <p className="break-words font-semibold">Step {step.step}</p>
          <p className="break-all text-sm text-muted">
            {step.tool?.name ?? step.decision?.action ?? "none"}
          </p>
        </div>
        <span className="max-w-[8rem] shrink-0 break-all rounded border border-line px-2 py-1 text-xs uppercase text-muted">
          {step.tool?.status ?? "unknown"}
        </span>
      </button>
      {hasNext && (
        <div className="ml-5 flex h-6 items-center text-muted">
          <GitBranch className="h-4 w-4" aria-hidden="true" />
        </div>
      )}
    </div>
  );
}

function EmptyPanel({ text }: { text: string }) {
  return (
    <section className="rounded-md border border-line bg-panel p-5 text-sm text-muted">
      {text}
    </section>
  );
}

export default ReverseAgentGraph;
