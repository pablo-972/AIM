import AnalysisHeader from "./AnalysisHeader";
import AnalysisOverview from "./AnalysisOverview";
import AnalysisStatus from "./AnalysisStatus";
import AnalysisTabs from "./AnalysisTabs";
import EnrichmentView from "../documents/EnrichmentView";
import ReportView from "../documents/ReportView";
import DynamicInferenceTrace from "../inference/DynamicInferenceTrace";
import StaticInferenceTrace from "../inference/StaticInferenceTrace";
import ReverseAgentGraph from "../reversing/ReverseAgentGraph";
import type { AnalysisArtifacts, AnalysisStatusPayload, AnalysisTab } from "../../types";

type AnalysisViewProps = {
  activeTab: AnalysisTab;
  artifacts: AnalysisArtifacts;
  reanalyzing: boolean;
  status: AnalysisStatusPayload | null;
  onReanalyze: () => void;
  onTabChange: (tab: AnalysisTab) => void;
};

function AnalysisView({
  activeTab,
  artifacts,
  reanalyzing,
  status,
  onReanalyze,
  onTabChange,
}: AnalysisViewProps) {
  const analysisData = isRecord(artifacts.analysisJson?.data) ? artifacts.analysisJson.data : null;
  const sample = isRecord(analysisData?.sample) ? analysisData.sample : null;
  const identifier = status?.sha256 ?? "Loading analysis";
  const sampleFilename = stringValue(sample?.filename) ?? status?.filename;
  const displayName = sampleFilename || identifier;
  const analysisActive = status?.status === "queued" || status?.status === "running";
  const reanalyzeDisabled = reanalyzing || analysisActive;

  return (
    <section className="space-y-5">
      <AnalysisHeader
        displayName={displayName}
        identifier={identifier}
        reanalyzeDisabled={reanalyzeDisabled}
        reanalyzing={reanalyzing}
        onReanalyze={onReanalyze}
      />

      {status && <AnalysisStatus status={status} />}

      <AnalysisTabs activeTab={activeTab} onTabChange={onTabChange} />

      {activeTab === "Overview" && (
        <AnalysisOverview status={status} artifact={artifacts.analysisJson} />
      )}
      {activeTab === "Static Inference" && (
        <StaticInferenceTrace trace={artifacts.staticInference} />
      )}
      {activeTab === "Dynamic Inference" && (
        <DynamicInferenceTrace trace={artifacts.dynamicInference} />
      )}
      {activeTab === "Enrichment" && <EnrichmentView artifact={artifacts.enrichment} />}
      {activeTab === "Reverse Agent" && <ReverseAgentGraph trace={artifacts.reverseAgent} />}
      {activeTab === "Report" && <ReportView artifact={artifacts.report} />}
    </section>
  );
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export default AnalysisView;
