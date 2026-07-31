import { RotateCcw } from "lucide-react";

type AnalysisHeaderProps = {
  displayName: string;
  identifier: string;
  reanalyzing: boolean;
  onReanalyze: () => void;
};

function AnalysisHeader({
  displayName,
  identifier,
  reanalyzing,
  onReanalyze,
}: AnalysisHeaderProps) {
  return (
    <div className="flex flex-col gap-4 rounded-md border border-line bg-panel p-5 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm uppercase text-muted">Sample</p>
        <h1 className="break-all text-xl font-semibold text-ink">
          {displayName}
        </h1>
        {displayName !== identifier && (
          <p className="mt-1 break-all text-sm leading-6 text-muted">
            SHA256: {identifier}
          </p>
        )}
      </div>
      <button
        type="button"
        onClick={onReanalyze}
        disabled={reanalyzing}
        className="inline-flex w-fit items-center gap-2 rounded border border-line bg-panelSoft px-3 py-2 text-sm font-medium text-ink transition hover:border-pink-500 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <RotateCcw className={`h-4 w-4 ${reanalyzing ? "animate-spin" : ""}`} aria-hidden="true" />
        Reanalyze
      </button>
    </div>
  );
}

export default AnalysisHeader;
