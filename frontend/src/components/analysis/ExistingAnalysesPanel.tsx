import { useEffect, useMemo, useState } from "react";
import { FolderOpen, RefreshCw } from "lucide-react";
import { getAnalyses } from "../../api";
import type { AnalysisStatusPayload } from "../../types";

type ExistingAnalysesPanelProps = {
  disabled: boolean;
  selectedSha256: string | null;
  onSelect: (analysis: AnalysisStatusPayload) => void;
};

function ExistingAnalysesPanel({
  disabled,
  selectedSha256,
  onSelect,
}: ExistingAnalysesPanelProps) {
  const [analyses, setAnalyses] = useState<AnalysisStatusPayload[]>([]);
  const [loading, setLoading] = useState(false);
  const uniqueAnalyses = useMemo(() => dedupeAnalyses(analyses), [analyses]);

  const refresh = async () => {
    setLoading(true);

    try {
      const payload = await getAnalyses();
      setAnalyses(payload.analyses);
    } catch {
      setAnalyses([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <section className="rounded-md border border-line bg-panel p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <FolderOpen className="h-5 w-5 text-pink-500" aria-hidden="true" />
          <div>
            <h2 className="text-lg font-semibold">Existing samples</h2>
            <p className="text-sm text-muted">workspace/analyses</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          className="inline-flex w-fit items-center gap-2 rounded border border-line bg-panelSoft px-3 py-2 text-sm text-ink transition hover:border-pink-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} aria-hidden="true" />
          Refresh
        </button>
      </div>

      {uniqueAnalyses.length ? (
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {uniqueAnalyses.map((analysis) => (
            <button
              key={analysis.sha256}
              type="button"
              onClick={() => onSelect(analysis)}
              disabled={disabled}
              className={`flex min-h-32 min-w-0 flex-col justify-between rounded border p-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
                selectedSha256 === analysis.sha256
                  ? "border-pink-500 bg-pink-500/10"
                  : "border-line bg-panelSoft hover:border-pink-500/70"
              }`}
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold" title={analysis.filename ?? analysis.sha256}>
                  {analysis.filename ?? analysis.sha256}
                </p>
                <p className="mt-2 break-all text-xs leading-relaxed text-muted">
                  {analysis.sha256}
                </p>
              </div>
              <p className="mt-4 text-xs font-semibold uppercase text-muted">
                {analysis.status}
              </p>
            </button>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted">No existing analyses found.</p>
      )}
    </section>
  );
}

function dedupeAnalyses(analyses: AnalysisStatusPayload[]): AnalysisStatusPayload[] {
  const seen = new Set<string>();
  const unique: AnalysisStatusPayload[] = [];

  for (const analysis of analyses) {
    const key = analysis.sha256;
    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    unique.push(analysis);
  }

  return unique;
}

export default ExistingAnalysesPanel;
