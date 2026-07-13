import { Bot, MessageSquareText } from "lucide-react";
import type { AgentTrace, JsonArtifact, TraceStep } from "../../types";
import JsonExpandable from "../common/JsonExpandable";

type StaticInferenceTraceProps = {
  trace: JsonArtifact<AgentTrace> | null;
};

function StaticInferenceTrace({ trace }: StaticInferenceTraceProps) {
  if (!trace?.available || !trace.data) {
    return <EmptyPanel text="Static inference trace is not available yet." />;
  }

  const steps = trace.data.steps ?? [];
  const findings = trace.data.findings ?? [];

  return (
    <section className="grid gap-5">
      <header className="rounded-md border border-line bg-panel p-5">
        <div className="flex items-center gap-3">
          <Bot className="h-5 w-5 text-accent" aria-hidden="true" />
          <div>
            <h2 className="text-lg font-semibold">Static Inference</h2>
            <p className="text-sm text-muted">{trace.data.status ?? "running"}</p>
          </div>
        </div>
      </header>

      <div className="grid gap-4">
        {steps.length ? (
          steps.map((step) => <StepCard key={step.step} step={step} />)
        ) : (
          <EmptyPanel text="No static inference steps recorded yet." />
        )}
      </div>

      <section className="rounded-md border border-line bg-panel p-5">
        <h2 className="mb-4 text-lg font-semibold">Findings</h2>
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
          <p className="text-sm text-muted">No findings recorded.</p>
        )}
      </section>
    </section>
  );
}

function StepCard({ step }: { step: TraceStep }) {
  const decision = step.decision ?? {};

  return (
    <article className="rounded-md border border-line bg-panel p-5">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <MessageSquareText className="h-5 w-5 text-accent" aria-hidden="true" />
          <div>
            <h3 className="font-semibold">Step {step.step}</h3>
            <p className="text-sm text-muted">{decision.action ?? "none"}</p>
          </div>
        </div>
        <span className="w-fit rounded border border-line bg-panelSoft px-2 py-1 text-xs uppercase text-muted">
          {decision.confidence ?? "unknown"}
        </span>
      </div>

      <div className="grid gap-3">
        <InfoBlock label="Thought" value={decision.thought || "No thought recorded."} />
        <InfoBlock label="Tool" value={step.tool?.name ?? "none"} />
        {step.error && <InfoBlock label="Error" value={step.error} tone="danger" />}
        {step.tool?.output && (
          <JsonExpandable data={step.tool.output} label="Tool output" />
        )}
        {step.finding && (
          <JsonExpandable data={step.finding} label="Finding" defaultOpen />
        )}
      </div>
    </article>
  );
}

function InfoBlock({
  label,
  value,
  tone = "normal",
}: {
  label: string;
  value: string;
  tone?: "normal" | "danger";
}) {
  return (
    <div className="rounded border border-line bg-panelSoft p-3">
      <p className="text-xs uppercase text-muted">{label}</p>
      <p className={`mt-1 text-sm ${tone === "danger" ? "text-red-200" : "text-ink"}`}>
        {value}
      </p>
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

export default StaticInferenceTrace;
