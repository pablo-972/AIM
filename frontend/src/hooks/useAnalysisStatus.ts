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
  sha256: string | null,
): UseAnalysisStatusResult {
  const [status, setStatus] = useState<AnalysisStatusPayload | null>(null);

  useEffect(() => {
    if (!sha256) {
      setStatus(null);
      return;
    }

    let cancelled = false;
    const pollStatus = async () => {
      try {
        const payload = await getStatus(sha256);
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
  }, [sha256]);

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
