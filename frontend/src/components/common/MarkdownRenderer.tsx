import ReactMarkdown from "react-markdown";

type MarkdownRendererProps = {
  content: string;
};

function MarkdownRenderer({ content }: MarkdownRendererProps) {
  if (!content.trim()) {
    return <p className="text-sm text-muted">No Markdown content available yet.</p>;
  }

  return (
    <div className="markdown rounded border border-line bg-slate-950/50 p-4">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}

export default MarkdownRenderer;
