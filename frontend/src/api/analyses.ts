import type { AnalysisListPayload, AnalysisStatusPayload } from "../types";

import { request } from "./client";

export async function createAnalysis(
  file: File,
  options: { reanalyze?: boolean } = {},
): Promise<AnalysisStatusPayload> {
  const form = new FormData();
  form.append("file", file);
  const query = options.reanalyze ? "?reanalyze=true" : "";

  return request<AnalysisStatusPayload>(
    `/api/analyses${query}`, 
    {
      method: "POST",
      body: form,
    }
  );
}

export function getAnalyses(): Promise<AnalysisListPayload> {
  return request<AnalysisListPayload>("/api/analyses");
}

export function resolveAnalysis(identifier: string): Promise<AnalysisStatusPayload> {
  const encodedIdentifier = encodeURIComponent(identifier);

  return request<AnalysisStatusPayload>(
    `/api/analyses/resolve/${encodedIdentifier}`,
  );
}

export function reanalyzeAnalysis(identifier: string): Promise<AnalysisStatusPayload> {
  const encodedIdentifier = encodeURIComponent(identifier);

  return request<AnalysisStatusPayload>(
    `/api/analyses/${encodedIdentifier}/reanalyze`,
    { 
      method: "POST" 
    },
  );
}

export function getStatus(analysisId: string): Promise<AnalysisStatusPayload> {
  const encodedAnalysisId = encodeURIComponent(analysisId);

  return request<AnalysisStatusPayload>(
    `/api/analyses/${encodedAnalysisId}/status`,
  );
}
