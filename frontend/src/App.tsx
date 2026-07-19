import { useCallback, useEffect, useState } from "react";

import {
  createAnalysis,
  reanalyzeAnalysis,
  resolveAnalysis,
} from "./api";
import AnalysisView from "./components/analysis/AnalysisView";
import HomeView from "./components/home/HomeView";
import Footer from "./components/layout/Footer";
import Navbar from "./components/layout/Navbar";
import { useAnalysisArtifacts } from "./hooks/useAnalysisArtifacts";
import { useAnalysisRoute } from "./hooks/useAnalysisRoute";
import { useAnalysisStatus } from "./hooks/useAnalysisStatus";
import { useElapsedTime } from "./hooks/useElapsedTime";
import { useTheme } from "./hooks/useTheme";
import type { AnalysisStatusPayload, AnalysisTab } from "./types";
import { formatElapsed } from "./utils/formatElapsed";

function App() {
  const { analysisId, navigateToAnalysis } = useAnalysisRoute();
  const { status, setStatus, isActive } = useAnalysisStatus(analysisId);
  const { artifacts, clearArtifacts } = useAnalysisArtifacts(analysisId, isActive);
  const { darkMode, toggleDarkMode } = useTheme();
  const elapsedSeconds = useElapsedTime(status?.created_at, isActive);

  const [activeTab, setActiveTab] = useState<AnalysisTab>("Overview");
  const [searching, setSearching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setActiveTab("Overview");
    clearArtifacts();
  }, [analysisId, clearArtifacts]);

  const loadAnalysis = useCallback((payload: AnalysisStatusPayload) => {
    const targetId = payload.sample_sha256 || payload.analysis_id;
    setStatus(payload);
    setActiveTab("Overview");
    clearArtifacts();
    setNotice(null);
    navigateToAnalysis(targetId);
  }, [clearArtifacts, navigateToAnalysis, setStatus]);

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
        onToggleTheme={toggleDarkMode}
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

        {analysisId === null && (
          <HomeView
            disabled={isActive || uploading}
            onAnalysisCreated={loadAnalysis}
          />
        )}

        {analysisId !== null && (
          <AnalysisView
            activeTab={activeTab}
            artifacts={artifacts}
            reanalyzing={reanalyzing}
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

export default App;
