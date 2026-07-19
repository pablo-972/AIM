export const analysisTabs = [
  "Overview",
  "Static Inference",
  "Dynamic Inference",
  "Enrichment",
  "Reverse Agent",
  "Report",
] as const;

export type AnalysisTab = (typeof analysisTabs)[number];
