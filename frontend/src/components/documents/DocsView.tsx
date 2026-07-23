import { useEffect, useMemo, useState } from "react";

import { getDocumentation } from "../../api";
import type { DocumentationPayload } from "../../types";
import MarkdownRenderer from "../common/MarkdownRenderer";

const docsSections = [
  {
    title: "Getting started",
    links: [
      { slug: "getting-started", label: "Overview" },
      { slug: "getting-started/configuration", label: "Configuration" },
      { slug: "getting-started/deployment", label: "Deployment" },
      { slug: "getting-started/malware-lab", label: "Malware lab" },
      { slug: "getting-started/software-agents", label: "Software agents" },
    ],
  },
  {
    title: "Phases",
    links: [
      { slug: "phases", label: "Overview" },
      { slug: "phases/static", label: "Static" },
      { slug: "phases/dynamic", label: "Dynamic" },
      { slug: "phases/enrichment", label: "Enrichment" },
      { slug: "phases/reversing", label: "Reversing" },
      { slug: "phases/report", label: "Report" },
    ],
  },
  {
    title: "Tools",
    links: [
      { slug: "tools", label: "Overview" },
      { slug: "tools/static", label: "Static" },
      { slug: "tools/dynamic", label: "Dynamic" },
      { slug: "tools/reversing", label: "Reversing" },
    ],
  },
  {
    title: "Project",
    links: [
      { slug: "architecture", label: "Architecture" },
      { slug: "ai", label: "AI" },
      { slug: "troubleshooting", label: "Troubleshooting" },
    ],
  },
] as const;

type DocsViewProps = {
  slug: string;
};

function DocsView({ slug }: DocsViewProps) {
  const normalizedSlug = slug || "getting-started";
  const [document, setDocument] = useState<DocumentationPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    setLoading(true);
    setError(null);

    getDocumentation(normalizedSlug)
      .then((payload) => {
        if (!active) {
          return;
        }
        setDocument(payload);
      })
      .catch((exc) => {
        if (!active) {
          return;
        }
        setDocument(null);
        setError(exc instanceof Error ? exc.message : String(exc));
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [normalizedSlug]);

  const content = useMemo(() => {
    if (!document) {
      return "";
    }

    return rewriteMarkdownDocLinks(document.content, document.slug);
  }, [document]);

  return (
    <div className="grid min-h-0 w-full gap-5 lg:grid-cols-[16rem_minmax(0,1fr)] xl:grid-cols-[16rem_minmax(0,56rem)_16rem] xl:justify-between">
      <aside className="rounded border border-line bg-panel p-3 lg:sticky lg:top-24 lg:max-h-[calc(100vh-7rem)] lg:self-start lg:overflow-y-auto">
        <h1 className="px-2 text-base font-bold text-ink">
          Documentation
        </h1>
        <nav className="mt-5 flex flex-col gap-5">
          {docsSections.map((section) => (
            <div key={section.title}>
              <h2 className="border-b border-line px-2 pb-1.5 text-sm font-bold text-ink">
                {section.title}
              </h2>
              <div className="mt-2 flex flex-col gap-0.5">
                {section.links.map((item) => (
                  <a
                    key={item.slug}
                    href={`/docs/${item.slug}`}
                    className={`rounded px-2 py-1 text-xs transition hover:bg-panelSoft hover:text-ink ${
                      item.slug === normalizedSlug
                        ? "bg-pink-500/10 text-pink-500"
                        : "text-muted"
                    }`}
                  >
                    {item.label}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      <section className="min-w-0">
        <div className="mx-auto w-full max-w-4xl">
          {loading && (
            <div className="rounded border border-line bg-panel p-4 text-sm text-muted">
              Loading documentation...
            </div>
          )}

          {error && (
            <div className="rounded border border-line bg-panel p-4 text-sm text-muted">
              Documentation page not found.
            </div>
          )}

          {!loading && !error && <MarkdownRenderer content={content} />}
          </div>
      </section>
    </div>
  );
}

function rewriteMarkdownDocLinks(content: string, currentSlug: string): string {
  return content.replace(
    /\]\((?!https?:\/\/|#|\/)([^)]+\.md(?:#[^)]+)?)\)/g,
    (_match, target: string) => {
      const [path, hash = ""] = target.split("#");
      const slug = resolveDocSlug(currentSlug, path);
      const suffix = hash ? `#${hash}` : "";

      return `](/docs/${slug}${suffix})`;
    },
  );
}

function resolveDocSlug(currentSlug: string, target: string): string {
  const base = currentSlug.includes("/")
    ? currentSlug.split("/").slice(0, -1)
    : [currentSlug];
  const parts = [...base, ...target.split("/")];
  const resolved: string[] = [];

  for (const part of parts) {
    if (!part || part === ".") {
      continue;
    }
    if (part === "..") {
      resolved.pop();
      continue;
    }
    resolved.push(part);
  }

  const last = resolved[resolved.length - 1];
  if (last?.endsWith(".md")) {
    resolved[resolved.length - 1] = last.slice(0, -3);
  }
  if (resolved[resolved.length - 1] === "README") {
    resolved.pop();
  }

  return resolved.join("/") || "getting-started";
}

export default DocsView;
