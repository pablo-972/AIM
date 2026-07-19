import { useCallback, useEffect, useState } from "react";

type UseAnalysisRouteResult = {
  analysisId: string | null;
  navigateToAnalysis: (identifier: string) => void;
};

function routeAnalysisId(): string | null {
  const match = window.location.pathname.match(/^\/analyses\/([^/]+)\/?$/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function useAnalysisRoute(): UseAnalysisRouteResult {
  const [analysisId, setAnalysisId] = useState<string | null>(routeAnalysisId());

  useEffect(() => {
    const onPopState = () => {
      setAnalysisId(routeAnalysisId());
    };

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigateToAnalysis = useCallback((identifier: string) => {
    const path = `/analyses/${encodeURIComponent(identifier)}`;
    setAnalysisId(identifier);

    if (window.location.pathname !== path) {
      window.history.pushState({}, "", path);
    }
  }, []);

  return {
    analysisId,
    navigateToAnalysis,
  };
}
