import { Activity, MessageSquareText } from "lucide-react";
import type { AgentTrace, JsonArtifact, TraceStep } from "../../types";
import JsonExpandable from "../common/JsonExpandable";

type DynamicInferenceTraceProps = {
  trace: JsonArtifact<AgentTrace> | null;
};

function DynamicInferenceTrace({ trace }: DynamicInferenceTraceProps) {
  if (!trace?.available || !trace.data) {
    return <EmptyPanel text="Dynamic inference trace is not available yet." />;
  }

  const steps = trace.data.steps ?? [];
  const findings = trace.data.findings ?? [];

  return (
    <section className="grid gap-5">
      <header className="rounded-md border border-line bg-panel p-5">
        <div className="flex items-center gap-3">
          <Activity className="h-5 w-5 text-accent" aria-hidden="true" />
          <div>
            <h2 className="text-lg font-semibold">Dynamic Inference</h2>
            <p className="text-sm text-muted">{trace.data.status ?? "running"}</p>
          </div>
        </div>
      </header>

      <section className="rounded-md border border-line bg-panel p-5">
        <h2 className="mb-4 text-lg font-semibold">Findings</h2>
        {findings.length ? (
          <div className="grid gap-3">
            {findings.map((finding, index) => (
              <FindingCard key={index} finding={finding} index={index} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">No dynamic findings recorded.</p>
        )}
      </section>

      <div className="grid gap-4">
        {steps.length ? (
          steps.map((step) => <StepCard key={step.step} step={step} />)
        ) : (
          <EmptyPanel text="No dynamic inference steps recorded yet." />
        )}
      </div>
    </section>
  );
}

function FindingCard({ finding, index }: { finding: unknown; index: number }) {
  const data = isRecord(finding) ? finding : {};

  return (
    <article className="rounded border border-line bg-panelSoft p-4">
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="font-semibold">
            {String(data.category ?? `Finding ${index + 1}`)}
          </h3>
          <p className="text-sm text-muted">{String(data.source ?? "unknown source")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge text={String(data.confidence ?? "unknown")} />
          <Badge text={String(data.tone ?? "unknown")} />
        </div>
      </div>

      <p className="mb-3 text-sm text-ink">
        {String(data.explanation ?? "No explanation recorded.")}
      </p>

      {"evidence" in data && (
        <JsonExpandable data={data.evidence} label="Evidence" />
      )}
    </article>
  );
}

function StepCard({ step }: { step: TraceStep }) {
  const decision = step.decision ?? {};
  const input = isRecord(step.input) ? step.input : {};

  return (
    <article className="rounded-md border border-line bg-panel p-5">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <MessageSquareText className="h-5 w-5 text-accent" aria-hidden="true" />
          <div>
            <h3 className="font-semibold">Step {step.step}</h3>
            <p className="text-sm text-muted">
              {String(input.tool ?? "unknown")}.{String(input.section ?? "unknown")}
            </p>
          </div>
        </div>
        <span className="w-fit rounded border border-line bg-panelSoft px-2 py-1 text-xs uppercase text-muted">
          {decision.confidence ?? "unknown"}
        </span>
      </div>

      <div className="grid gap-3">
        <InfoBlock label="Thought" value={decision.thought || "No thought recorded."} />
        <InfoBlock label="Action" value={decision.action || "none"} />
        {step.error && <InfoBlock label="Error" value={step.error} tone="danger" />}
        {step.finding && (
          <JsonExpandable data={step.finding} label="Finding" defaultOpen />
        )}
      </div>
    </article>
  );
}

function Badge({ text }: { text: string }) {
  return (
    <span className="w-fit rounded border border-line bg-panelSoft px-2 py-1 text-xs uppercase text-muted">
      {text}
    </span>
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export default DynamicInferenceTrace;
