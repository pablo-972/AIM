import { useEffect, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";

import { getStatus } from "../api";
import type { AnalysisStatusPayload } from "../types";

type UseAnalysisStatusResult = {
  status: AnalysisStatusPayload | null;
  setStatus: Dispatch<SetStateAction<AnalysisStatusPayload | null>>;
  isActive: boolean;
};

export function useAnalysisStatus(
  analysisId: string | null,
): UseAnalysisStatusResult {
  const [status, setStatus] = useState<AnalysisStatusPayload | null>(null);

  useEffect(() => {
    if (!analysisId) {
      setStatus(null);
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

  const isActive = useMemo(
    () => status?.status === "queued" || status?.status === "running",
    [status?.status],
  );

  return {
    status,
    setStatus,
    isActive,
  };
}
