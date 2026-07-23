import { useEffect, useId, useState } from "react";

type MermaidDiagramProps = {
  chart: string;
};

function MermaidDiagram({ chart }: MermaidDiagramProps) {
  const rawId = useId();
  const diagramId = `mermaid-${rawId.replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    setSvg(null);
    setError(null);

    async function renderDiagram() {
      try {
        const mermaidModule = await import("mermaid");
        const mermaid = mermaidModule.default;
        const darkMode = document.documentElement.classList.contains("dark");

        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: darkMode ? "dark" : "default",
        });

        const result = await mermaid.render(diagramId, chart);
        if (active) {
          setSvg(result.svg);
        }
      } catch (exc) {
        if (active) {
          setError(exc instanceof Error ? exc.message : String(exc));
        }
      }
    }

    void renderDiagram();

    return () => {
      active = false;
    };
  }, [chart, diagramId]);

  if (error) {
    return (
      <pre className="mermaid-fallback">
        <code>{chart}</code>
      </pre>
    );
  }

  if (!svg) {
    return (
      <div className="mermaid-diagram text-sm text-muted">
        Rendering diagram...
      </div>
    );
  }

  return (
    <div
      className="mermaid-diagram"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

export default MermaidDiagram;
