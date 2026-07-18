import { useEffect, useMemo, useState } from "react";
import { FolderOpen, RefreshCw } from "lucide-react";
import { getAnalyses } from "../../api";
import type { AnalysisStatusPayload } from "../../types";

type ExistingAnalysesPanelProps = {
  disabled: boolean;
  selectedAnalysisId: string | null;
  onSelect: (analysis: AnalysisStatusPayload) => void;
};

function ExistingAnalysesPanel({
  disabled,
  selectedAnalysisId,
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
              key={analysis.analysis_id}
              type="button"
              onClick={() => onSelect(analysis)}
              disabled={disabled}
              className={`min-w-0 rounded border p-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${
                selectedAnalysisId === analysis.analysis_id
                  ? "border-pink-500 bg-pink-500/10"
                  : "border-line bg-panelSoft hover:border-pink-500/70"
              }`}
            >
              <p className="break-all text-sm font-semibold">{analysis.analysis_id}</p>
              <p className="mt-1 break-all text-xs text-muted">
                {analysis.sample_sha256 ?? analysis.filename ?? "no sample metadata"}
              </p>
              <p className="mt-2 text-xs uppercase text-muted">{analysis.status}</p>
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
    const key = analysis.sample_sha256 || analysis.analysis_id;
    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    unique.push(analysis);
  }

  return unique;
}

export default ExistingAnalysesPanel;
