import { useEffect, useMemo, useState } from "react";
import {
  getAnalysisJson,
  getDynamicInference,
  getEnrichment,
  getReport,
  getReverseAgent,
  getStaticInference,
  getStatus,
} from "./api";
import AnalysisOverview from "./components/analysis/AnalysisOverview";
import AnalysisStatus from "./components/analysis/AnalysisStatus";
import ExistingAnalysesPanel from "./components/analysis/ExistingAnalysesPanel";
import UploadPanel from "./components/analysis/UploadPanel";
import EnrichmentView from "./components/documents/EnrichmentView";
import ReportView from "./components/documents/ReportView";
import DynamicInferenceTrace from "./components/inference/DynamicInferenceTrace";
import StaticInferenceTrace from "./components/inference/StaticInferenceTrace";
import ReverseAgentGraph from "./components/reversing/ReverseAgentGraph";
import type {
  AgentTrace,
  AnalysisStatusPayload,
  JsonArtifact,
  TextArtifact,
} from "./types";

const tabs = [
  "Overview",
  "Static Inference",
  "Dynamic Inference",
  "Enrichment",
  "Reverse Agent",
  "Report",
] as const;
type Tab = (typeof tabs)[number];

function App() {
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [status, setStatus] = useState<AnalysisStatusPayload | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const [analysisJson, setAnalysisJson] = useState<JsonArtifact | null>(null);
  const [staticInference, setStaticInference] = useState<JsonArtifact<AgentTrace> | null>(null);
  const [dynamicInference, setDynamicInference] = useState<JsonArtifact<AgentTrace> | null>(null);
  const [enrichment, setEnrichment] = useState<TextArtifact | null>(null);
  const [reverseAgent, setReverseAgent] = useState<JsonArtifact<AgentTrace> | null>(null);
  const [report, setReport] = useState<TextArtifact | null>(null);

  const isActive = useMemo(
    () => status?.status === "queued" || status?.status === "running",
    [status?.status],
  );

  const clearArtifacts = () => {
    setAnalysisJson(null);
    setStaticInference(null);
    setDynamicInference(null);
    setEnrichment(null);
    setReverseAgent(null);
    setReport(null);
  };

  const loadAnalysis = (payload: AnalysisStatusPayload) => {
    setAnalysisId(payload.analysis_id);
    setStatus(payload);
    setActiveTab("Overview");
    clearArtifacts();
  };

  useEffect(() => {
    if (!analysisId) {
      return;
    }

    let cancelled = false;
    const pollStatus = async () => {
      try {
        const payload = await getStatus(analysisId);
        if (!cancelled) {
          setStatus(payload);
        }
      } catch (error) {
        if (!cancelled) {
          setStatus((previous) =>
            previous
              ? { ...previous, status: "failed", error: String(error) }
              : previous,
          );
        }
      }
    };

    void pollStatus();
    const interval = window.setInterval(pollStatus, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [analysisId]);

  useEffect(() => {
    if (!analysisId) {
      return;
    }

    let cancelled = false;
    const pollArtifacts = async () => {
      const artifactRequests = [
        getAnalysisJson(analysisId),
        getStaticInference(analysisId),
        getDynamicInference(analysisId),
        getEnrichment(analysisId),
        getReverseAgent(analysisId),
        getReport(analysisId),
      ] as const;
      const results = await Promise.allSettled(artifactRequests) as [
        PromiseSettledResult<JsonArtifact>,
        PromiseSettledResult<JsonArtifact<AgentTrace>>,
        PromiseSettledResult<JsonArtifact<AgentTrace>>,
        PromiseSettledResult<TextArtifact>,
        PromiseSettledResult<JsonArtifact<AgentTrace>>,
        PromiseSettledResult<TextArtifact>,
      ];

      if (cancelled) {
        return;
      }

      if (results[0].status === "fulfilled") setAnalysisJson(results[0].value);
      if (results[1].status === "fulfilled") setStaticInference(results[1].value);
      if (results[2].status === "fulfilled") setDynamicInference(results[2].value);
      if (results[3].status === "fulfilled") setEnrichment(results[3].value);
      if (results[4].status === "fulfilled") setReverseAgent(results[4].value);
      if (results[5].status === "fulfilled") setReport(results[5].value);
    };

    void pollArtifacts();
    const interval = window.setInterval(pollArtifacts, isActive ? 1000 : 8000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [analysisId, isActive]);

  return (
    <main className="min-h-screen bg-slate-950 text-ink">
      <section className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-5 py-8 sm:px-8 lg:px-10">
        <header className="text-center">
          <h1 className="text-4xl font-semibold tracking-normal sm:text-5xl">AIM</h1>
        </header>

        <UploadPanel
          disabled={isActive}
          onAnalysisCreated={loadAnalysis}
        />

        <ExistingAnalysesPanel
          disabled={isActive}
          selectedAnalysisId={analysisId}
          onSelect={loadAnalysis}
        />

        {status && <AnalysisStatus status={status} />}

        {analysisId && (
          <section className="space-y-5">
            <nav className="flex flex-wrap gap-2 rounded-md border border-line bg-panel p-2">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  className={`rounded px-3 py-2 text-sm font-medium transition ${
                    activeTab === tab
                      ? "bg-accent text-slate-950"
                      : "text-muted hover:bg-panelSoft hover:text-ink"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </nav>

            {activeTab === "Overview" && (
              <AnalysisOverview status={status} artifact={analysisJson} />
            )}
            {activeTab === "Static Inference" && (
              <StaticInferenceTrace trace={staticInference} />
            )}
            {activeTab === "Dynamic Inference" && (
              <DynamicInferenceTrace trace={dynamicInference} />
            )}
            {activeTab === "Enrichment" && <EnrichmentView artifact={enrichment} />}
            {activeTab === "Reverse Agent" && <ReverseAgentGraph trace={reverseAgent} />}
            {activeTab === "Report" && <ReportView artifact={report} />}
          </section>
        )}
      </section>
    </main>
  );
}

export default App;
