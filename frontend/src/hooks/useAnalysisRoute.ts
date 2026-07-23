import { useCallback, useEffect, useState } from "react";

type UseAnalysisRouteResult = {
  analysisId: string | null;
  docsSlug: string | null;
  navigateToAnalysis: (identifier: string) => void;
};

function routeAnalysisId(): string | null {
  const match = window.location.pathname.match(/^\/analyses\/([^/]+)\/?$/);
  return match ? decodeURIComponent(match[1]) : null;
}

function routeDocsSlug(): string | null {
  const match = window.location.pathname.match(/^\/docs(?:\/(.+))?\/?$/);
  if (!match) {
    return null;
  }

  return match[1] ? decodeURIComponent(match[1]) : "getting-started";
}

export function useAnalysisRoute(): UseAnalysisRouteResult {
  const [analysisId, setAnalysisId] = useState<string | null>(routeAnalysisId());
  const [docsSlug, setDocsSlug] = useState<string | null>(routeDocsSlug());

  useEffect(() => {
    const onPopState = () => {
      setAnalysisId(routeAnalysisId());
      setDocsSlug(routeDocsSlug());
    };

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigateToAnalysis = useCallback((identifier: string) => {
    const path = `/analyses/${encodeURIComponent(identifier)}`;
    setAnalysisId(identifier);
    setDocsSlug(null);

    if (window.location.pathname !== path) {
      window.history.pushState({}, "", path);
    }
  }, []);

  return {
    analysisId,
    docsSlug,
    navigateToAnalysis,
  };
}
