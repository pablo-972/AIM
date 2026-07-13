import { ScrollText } from "lucide-react";
import type { TextArtifact } from "../../types";
import MarkdownRenderer from "../common/MarkdownRenderer";

type ReportViewProps = {
  artifact: TextArtifact | null;
};

function ReportView({ artifact }: ReportViewProps) {
  return (
    <section className="rounded-md border border-line bg-panel p-5">
      <div className="mb-4 flex items-center gap-3">
        <ScrollText className="h-5 w-5 text-accent" aria-hidden="true" />
        <div>
          <h2 className="text-lg font-semibold">Report</h2>
          <p className="text-sm text-muted">
            {artifact?.available ? "Final or current report.md" : "Waiting for report.md"}
          </p>
        </div>
      </div>
      <MarkdownRenderer content={artifact?.content ?? ""} />
    </section>
  );
}

export default ReportView;
