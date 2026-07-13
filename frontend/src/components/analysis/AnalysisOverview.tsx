import type { ReactNode } from "react";
import type { AnalysisStatusPayload, JsonArtifact } from "../../types";
import JsonExpandable from "../common/JsonExpandable";

type AnalysisOverviewProps = {
  status: AnalysisStatusPayload;
  artifact: JsonArtifact | null;
};

type ToolEntry = [string, Record<string, unknown>];

function AnalysisOverview({ status, artifact }: AnalysisOverviewProps) {
  const data = isRecord(artifact?.data) ? artifact.data : null;
  const sample = isRecord(data?.["sample"]) ? data["sample"] : null;
  const phases = isRecord(data?.["phases"]) ? data["phases"] : null;
  const staticPhase = isRecord(phases?.["static"]) ? phases["static"] : null;
  const dynamicPhase = isRecord(phases?.["dynamic"]) ? phases["dynamic"] : null;
  const reversePhase = isRecord(phases?.["reversing"]) ? phases["reversing"] : null;

  return (
    <section className="grid gap-5">
      <Panel title="Sample">
        {sample ? (
          <dl className="grid gap-3 text-sm sm:grid-cols-3">
            {Object.entries(sample).map(([key, value]) => (
              <div key={key} className="rounded border border-line bg-panelSoft p-3">
                <dt className="text-xs uppercase text-muted">{key}</dt>
                <dd className="mt-1 break-all text-ink">{String(value)}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <Empty text={`Waiting for analysis.json for ${status.filename ?? "sample"}.`} />
        )}
      </Panel>

      <Panel title="Static Phase">
        <PhaseTools phase={staticPhase} />
      </Panel>

      <Panel title="Dynamic Phase">
        <PhaseTools phase={dynamicPhase} />
      </Panel>

      <Panel title="Reverse Phase">
        {reversePhase ? <PhaseTools phase={reversePhase} /> : <Empty text="No reverse phase data yet." />}
      </Panel>

      <Panel title="Errors">
        {status.error ? (
          <p className="text-sm text-danger">{status.error}</p>
        ) : (
          <Empty text="No pipeline errors reported." />
        )}
      </Panel>
    </section>
  );
}

function PhaseTools({ phase }: { phase: Record<string, unknown> | null }) {
  if (!phase) {
    return <Empty text="No phase data yet." />;
  }

  const tools = isRecord(phase.tools) ? phase.tools : {};
  const entries = Object.entries(tools).filter((entry): entry is ToolEntry =>
    isRecord(entry[1]),
  );

  if (!entries.length) {
    return <Empty text="No tools recorded yet." />;
  }

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      {entries.map(([toolName, tool]) => (
        <article key={toolName} className="rounded border border-line bg-panelSoft p-4">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold">{toolName}</h3>
              <p className="text-xs uppercase text-muted">
                {String(tool.success === false ? "failed" : "completed")}
              </p>
            </div>
            <span
              className={`rounded border px-2 py-1 text-xs ${
                tool.success === false
                  ? "border-danger/40 text-red-200"
                  : "border-emerald-500/40 text-emerald-200"
              }`}
            >
              {tool.success === false ? "error" : "ok"}
            </span>
          </div>
          <Metadata data={tool} />
          <JsonExpandable data={tool} label="Show output" />
        </article>
      ))}
    </div>
  );
}

function Metadata({ data }: { data: Record<string, unknown> }) {
  const compact = Object.entries(data).filter(([, value]) => !isRecord(value) && !Array.isArray(value));
  if (!compact.length) {
    return null;
  }

  return (
    <dl className="mb-3 grid gap-2 text-xs sm:grid-cols-2">
      {compact.slice(0, 6).map(([key, value]) => (
        <div key={key} className="rounded bg-slate-950/60 p-2">
          <dt className="uppercase text-muted">{key}</dt>
          <dd className="mt-1 break-all text-slate-200">{String(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-md border border-line bg-panel p-5">
      <h2 className="mb-4 text-lg font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-sm text-muted">{text}</p>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export default AnalysisOverview;
