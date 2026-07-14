import { FileText } from "lucide-react";
import type { TextArtifact } from "../../types";
import MarkdownRenderer from "../common/MarkdownRenderer";

type EnrichmentViewProps = {
  artifact: TextArtifact | null;
};

function EnrichmentView({ artifact }: EnrichmentViewProps) {
  return (
    <section className="rounded-md border border-line bg-panel p-5">
      <div className="mb-4 flex items-center gap-3">
        <FileText className="h-5 w-5 text-accent" aria-hidden="true" />
        <div>
          <h2 className="text-lg font-semibold">Enrichment</h2>
          <p className="text-sm text-muted">
            {artifact?.available ? "Final or current enrichment.md" : "Waiting for enrichment.md"}
          </p>
        </div>
      </div>
      <MarkdownRenderer content={artifact?.content ?? ""} />
    </section>
  );
}

export default EnrichmentView;
