import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

type JsonExpandableProps = {
  data: unknown;
  label?: string;
  defaultOpen?: boolean;
  maxPreviewLength?: number;
};

function JsonExpandable({
  data,
  label = "JSON",
  defaultOpen = false,
  maxPreviewLength = 220,
}: JsonExpandableProps) {
  const [open, setOpen] = useState(defaultOpen);
  const serialized = useMemo(() => JSON.stringify(data ?? null, null, 2) ?? "null", [data]);
  const preview = serialized.length > maxPreviewLength
    ? `${serialized.slice(0, maxPreviewLength)}...`
    : serialized;

  return (
    <div className="min-w-0 overflow-hidden rounded border border-line bg-slate-950/70">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full min-w-0 items-center justify-between gap-3 px-3 py-2 text-left text-sm text-ink hover:bg-panelSoft"
      >
        <span className="min-w-0 break-words font-medium">{label}</span>
        {open ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
        )}
      </button>
      <pre className="max-h-[34rem] overflow-y-auto overflow-x-hidden whitespace-pre-wrap break-all border-t border-line p-3 text-xs leading-relaxed text-slate-200">
        {open ? serialized : preview}
      </pre>
    </div>
  );
}

export default JsonExpandable;
