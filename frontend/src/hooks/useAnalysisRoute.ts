import { useCallback, useEffect, useState } from "react";

type UseAnalysisRouteResult = {
  sha256: string | null;
  docsSlug: string | null;
  navigateToAnalysis: (identifier: string) => void;
};

function routeSha256(): string | null {
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
  const [sha256, setSha256] = useState<string | null>(routeSha256());
  const [docsSlug, setDocsSlug] = useState<string | null>(routeDocsSlug());

  useEffect(() => {
    const onPopState = () => {
      setSha256(routeSha256());
      setDocsSlug(routeDocsSlug());
    };

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigateToAnalysis = useCallback((identifier: string) => {
    const path = `/analyses/${encodeURIComponent(identifier)}`;
    setSha256(identifier);
    setDocsSlug(null);

    if (window.location.pathname !== path) {
      window.history.pushState({}, "", path);
    }
  }, []);

  return {
    sha256,
    docsSlug,
    navigateToAnalysis,
  };
}
