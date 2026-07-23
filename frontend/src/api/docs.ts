import type { DocumentationPayload } from "../types";

import { request } from "./client";

export function getDocumentation(slug: string): Promise<DocumentationPayload> {
  const encodedSlug = slug
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/");

  return request<DocumentationPayload>(`/api/docs/${encodedSlug}`);
}
