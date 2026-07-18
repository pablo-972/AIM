import { useEffect, useMemo, useState } from "react";
import { RotateCcw } from "lucide-react";
import {
  createAnalysis,
  getAnalysisJson,
  getDynamicInference,
  getEnrichment,
  getReport,
  getReverseAgent,
  getStaticInference,
  getStatus,
  reanalyzeAnalysis,
  resolveAnalysis,
} from "./api";
import AnalysisOverview from "./components/analysis/AnalysisOverview";
import AnalysisStatus from "./components/analysis/AnalysisStatus";
import UploadPanel from "./components/analysis/UploadPanel";
import EnrichmentView from "./components/documents/EnrichmentView";
import ReportView from "./components/documents/ReportView";
import DynamicInferenceTrace from "./components/inference/DynamicInferenceTrace";
import StaticInferenceTrace from "./components/inference/StaticInferenceTrace";
import Footer from "./components/layout/Footer";
import Navbar from "./components/layout/Navbar";
import LogoMark from "./components/layout/LogoMark";
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
  const [analysisId, setAnalysisId] = useState<string | null>(routeAnalysisId());
  const [status, setStatus] = useState<AnalysisStatusPayload | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const [analysisJson, setAnalysisJson] = useState<JsonArtifact | null>(null);
  const [staticInference, setStaticInference] = useState<JsonArtifact<AgentTrace> | null>(null);
  const [dynamicInference, setDynamicInference] = useState<JsonArtifact<AgentTrace> | null>(null);
  const [enrichment, setEnrichment] = useState<TextArtifact | null>(null);
  const [reverseAgent, setReverseAgent] = useState<JsonArtifact<AgentTrace> | null>(null);
  const [report, setReport] = useState<TextArtifact | null>(null);
  const [darkMode, setDarkMode] = useState(() => prefersDarkMode());
  const [searching, setSearching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const isActive = useMemo(
    () => status?.status === "queued" || status?.status === "running",
    [status?.status],
  );
  const currentRouteId = routeAnalysisId();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  useEffect(() => {
    const onPopState = () => {
      const nextId = routeAnalysisId();
      setAnalysisId(nextId);
      setActiveTab("Overview");
      clearArtifacts();
    };

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (!analysisId) {
      setStatus(null);
      clearArtifacts();
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

  useEffect(() => {
    if (!isActive || !status?.created_at) {
      setElapsedSeconds(0);
      return;
    }

    const startedAt = Date.parse(status.created_at);
    const tick = () => {
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    };

    tick();
    const interval = window.setInterval(tick, 1000);
    return () => window.clearInterval(interval);
  }, [isActive, status?.created_at]);

  const clearArtifacts = () => {
    setAnalysisJson(null);
    setStaticInference(null);
    setDynamicInference(null);
    setEnrichment(null);
    setReverseAgent(null);
    setReport(null);
  };

  const loadAnalysis = (payload: AnalysisStatusPayload) => {
    const targetId = payload.sample_sha256 || payload.analysis_id;
    setAnalysisId(targetId);
    setStatus(payload);
    setActiveTab("Overview");
    clearArtifacts();
    setNotice(null);
    pushAnalysisRoute(targetId);
  };

  const handleSearch = async (value: string) => {
    const query = value.trim();
    if (!query) {
      return;
    }

    setSearching(true);
    setNotice(null);
    try {
      const payload = await resolveAnalysis(query);
      loadAnalysis(payload);
    } catch {
      setNotice("No existing analysis found for that hash.");
    } finally {
      setSearching(false);
    }
  };

  const handleUpload = async (file: File) => {
    setUploading(true);
    setNotice(null);
    try {
      const payload = await createAnalysis(file);
      loadAnalysis(payload);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setUploading(false);
    }
  };

  const handleReanalyze = async () => {
    const identifier = status?.sample_sha256 || analysisId;
    if (!identifier) {
      return;
    }

    setReanalyzing(true);
    setNotice(null);
    try {
      const payload = await reanalyzeAnalysis(identifier);
      loadAnalysis(payload);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setReanalyzing(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-page text-ink">
      <Navbar
        darkMode={darkMode}
        existingDisabled={isActive || uploading}
        selectedAnalysisId={status?.sample_sha256 ?? analysisId}
        searching={searching}
        uploading={uploading}
        onSelectExisting={loadAnalysis}
        onSearch={handleSearch}
        onUpload={handleUpload}
        onToggleTheme={() => setDarkMode((current) => !current)}
      />

      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-8 px-5 py-6 sm:px-8 lg:px-10">
        {notice && (
          <div className="rounded border border-line bg-panel p-3 text-sm text-muted">
            {notice}
          </div>
        )}

        {isActive && status && (
          <div className="flex flex-col gap-1 rounded border border-pink-500/40 bg-pink-500/10 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
            <span className="font-medium text-ink">
              Analysis running: {status.current_phase ?? status.status}
            </span>
            <span className="tabular-nums text-muted">
              Elapsed {formatElapsed(elapsedSeconds)}
            </span>
          </div>
        )}

        {!currentRouteId && (
          <HomeView
            disabled={isActive || uploading}
            onAnalysisCreated={loadAnalysis}
          />
        )}

        {currentRouteId && (
          <AnalysisView
            activeTab={activeTab}
            analysisJson={analysisJson}
            dynamicInference={dynamicInference}
            enrichment={enrichment}
            reanalyzing={reanalyzing}
            report={report}
            reverseAgent={reverseAgent}
            staticInference={staticInference}
            status={status}
            onReanalyze={handleReanalyze}
            onTabChange={setActiveTab}
          />
        )}
      </main>

      <Footer />
    </div>
  );
}

type HomeViewProps = {
  disabled: boolean;
  onAnalysisCreated: (status: AnalysisStatusPayload) => void;
};

function HomeView({ disabled, onAnalysisCreated }: HomeViewProps) {
  return (
    <>
      <section className="flex flex-col items-center justify-center gap-6 py-8 text-center sm:py-12">
        <div className="flex items-center gap-5">
          <LogoMark size="lg" showName={false} />
          <h1 className="text-5xl font-semibold tracking-normal text-pink-500 sm:text-7xl">
            AIM
          </h1>
        </div>
        <p className="max-w-3xl text-base leading-7 text-muted sm:text-lg">
          Analyze binaries using a traditional malware analysis workflow enhanced with AI-powered behavioral inference, 
          iterative context enrichment, an autonomous reverse engineering agent, and comprehensive technical report generation.
        </p>
      </section>

      <UploadPanel
        disabled={disabled}
        onAnalysisCreated={onAnalysisCreated}
      />
    </>
  );
}

type AnalysisViewProps = {
  activeTab: Tab;
  analysisJson: JsonArtifact | null;
  dynamicInference: JsonArtifact<AgentTrace> | null;
  enrichment: TextArtifact | null;
  reanalyzing: boolean;
  report: TextArtifact | null;
  reverseAgent: JsonArtifact<AgentTrace> | null;
  staticInference: JsonArtifact<AgentTrace> | null;
  status: AnalysisStatusPayload | null;
  onReanalyze: () => void;
  onTabChange: (tab: Tab) => void;
};

function AnalysisView({
  activeTab,
  analysisJson,
  dynamicInference,
  enrichment,
  reanalyzing,
  report,
  reverseAgent,
  staticInference,
  status,
  onReanalyze,
  onTabChange,
}: AnalysisViewProps) {
  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-4 rounded-md border border-line bg-panel p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm uppercase text-muted">Sample</p>
          <h1 className="break-all text-xl font-semibold text-ink">
            {status?.sample_sha256 ?? status?.analysis_id ?? "Loading analysis"}
          </h1>
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

      {status && <AnalysisStatus status={status} />}

      <nav className="flex flex-wrap gap-2 rounded-md border border-line bg-panel p-2">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => onTabChange(tab)}
            className={`rounded px-3 py-2 text-sm font-medium transition ${
              activeTab === tab
                ? "bg-pink-500 text-white"
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
  );
}

function routeAnalysisId(): string | null {
  const match = window.location.pathname.match(/^\/analyses\/([^/]+)\/?$/);
  return match ? decodeURIComponent(match[1]) : null;
}

function pushAnalysisRoute(identifier: string) {
  const path = `/analyses/${encodeURIComponent(identifier)}`;
  if (window.location.pathname !== path) {
    window.history.pushState({}, "", path);
  }
}

function prefersDarkMode(): boolean {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? true;
}

function formatElapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
}

export default App;
