import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import MermaidDiagram from "./MermaidDiagram";

type MarkdownRendererProps = {
  content: string;
};

const markdownComponents: Components = {
  code({ className, children, node: _node, ...props }) {
    const code = String(children).replace(/\n$/, "");
    const isMermaid = /\blanguage-mermaid\b/.test(className || "");

    if (isMermaid) {
      return <MermaidDiagram chart={code} />;
    }

    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
};

function MarkdownRenderer({ content }: MarkdownRendererProps) {
  if (!content.trim()) {
    return <p className="text-sm text-muted">No Markdown content available yet.</p>;
  }

  return (
    <div className="markdown rounded border border-line bg-panel p-4">
      <ReactMarkdown
        components={markdownComponents}
        remarkPlugins={[remarkGfm]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default MarkdownRenderer;
