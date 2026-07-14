import type {
  AgentTrace,
  AnalysisListPayload,
  AnalysisStatusPayload,
  JsonArtifact,
  TextArtifact,
} from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function createAnalysis(file: File): Promise<AnalysisStatusPayload> {
  const form = new FormData();
  form.append("file", file);

  return request<AnalysisStatusPayload>("/api/analyses", {
    method: "POST",
    body: form,
  });
}

export function getAnalyses(): Promise<AnalysisListPayload> {
  return request<AnalysisListPayload>("/api/analyses");
}

export function getStatus(analysisId: string): Promise<AnalysisStatusPayload> {
  return request<AnalysisStatusPayload>(`/api/analyses/${analysisId}/status`);
}

export function getAnalysisJson(analysisId: string): Promise<JsonArtifact> {
  return request<JsonArtifact>(`/api/analyses/${analysisId}/analysis-json`);
}

export function getStaticInference(analysisId: string): Promise<JsonArtifact<AgentTrace>> {
  return request<JsonArtifact<AgentTrace>>(`/api/analyses/${analysisId}/static-inference`);
}

export function getDynamicInference(analysisId: string): Promise<JsonArtifact<AgentTrace>> {
  return request<JsonArtifact<AgentTrace>>(`/api/analyses/${analysisId}/dynamic-inference`);
}

export function getEnrichment(analysisId: string): Promise<TextArtifact> {
  return request<TextArtifact>(`/api/analyses/${analysisId}/enrichment`);
}

export function getReverseAgent(analysisId: string): Promise<JsonArtifact<AgentTrace>> {
  return request<JsonArtifact<AgentTrace>>(`/api/analyses/${analysisId}/reverse-agent`);
}

export function getReport(analysisId: string): Promise<TextArtifact> {
  return request<TextArtifact>(`/api/analyses/${analysisId}/report`);
}
