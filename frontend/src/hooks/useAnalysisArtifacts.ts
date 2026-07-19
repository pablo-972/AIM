import { useCallback, useEffect, useState } from "react";

import {
  getAnalysisJson,
  getDynamicInference,
  getEnrichment,
  getReport,
  getReverseAgent,
  getStaticInference,
} from "../api";
import type { AgentTrace, AnalysisArtifacts, JsonArtifact, TextArtifact } from "../types";

type UseAnalysisArtifactsResult = {
  artifacts: AnalysisArtifacts;
  clearArtifacts: () => void;
};

const emptyArtifacts: AnalysisArtifacts = {
  analysisJson: null,
  staticInference: null,
  dynamicInference: null,
  enrichment: null,
  reverseAgent: null,
  report: null,
};

export function useAnalysisArtifacts(
  analysisId: string | null,
  isActive: boolean,
): UseAnalysisArtifactsResult {
  const [artifacts, setArtifacts] = useState<AnalysisArtifacts>(emptyArtifacts);

  const clearArtifacts = useCallback(() => {
    setArtifacts(emptyArtifacts);
  }, []);

  useEffect(() => {
    if (!analysisId) {
      clearArtifacts();
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

      setArtifacts((current) => ({
        analysisJson: results[0].status === "fulfilled" ? results[0].value : current.analysisJson,
        staticInference: results[1].status === "fulfilled" ? results[1].value : current.staticInference,
        dynamicInference: results[2].status === "fulfilled" ? results[2].value : current.dynamicInference,
        enrichment: results[3].status === "fulfilled" ? results[3].value : current.enrichment,
        reverseAgent: results[4].status === "fulfilled" ? results[4].value : current.reverseAgent,
        report: results[5].status === "fulfilled" ? results[5].value : current.report,
      }));
    };

    void pollArtifacts();
    const interval = window.setInterval(pollArtifacts, isActive ? 1000 : 8000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [analysisId, clearArtifacts, isActive]);

  return {
    artifacts,
    clearArtifacts,
  };
}
