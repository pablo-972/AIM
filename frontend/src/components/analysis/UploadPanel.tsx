import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { FileUp, Loader2, UploadCloud } from "lucide-react";
import { createAnalysis } from "../../api";
import type { AnalysisStatusPayload } from "../../types";

type UploadPanelProps = {
  disabled: boolean;
  onAnalysisCreated: (status: AnalysisStatusPayload) => void;
};

function UploadPanel({ disabled, onAnalysisCreated }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upload = async (file: File | undefined) => {
    if (!file || disabled || uploading) {
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const status = await createAnalysis(file);
      onAnalysisCreated(status);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    void upload(event.dataTransfer.files[0]);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    void upload(event.target.files?.[0]);
    event.target.value = "";
  };

  return (
    <section className="space-y-4">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`flex min-h-64 flex-col items-center justify-center rounded-md border border-dashed p-8 text-center shadow-glow transition ${
          dragging
            ? "border-accent bg-teal-950/30"
            : "border-line bg-panel hover:border-accent/70"
        } ${disabled ? "opacity-70" : ""}`}
      >
        <div className="mb-4 rounded-md border border-line bg-panelSoft p-4 text-accent">
          {uploading ? (
            <Loader2 className="h-9 w-9 animate-spin" aria-hidden="true" />
          ) : (
            <UploadCloud className="h-9 w-9" aria-hidden="true" />
          )}
        </div>
        <p className="text-lg font-semibold">Drop malware binary here</p>
        <p className="mt-2 max-w-xl text-sm text-muted">
          Upload starts the full local AIM pipeline automatically.
        </p>
      </div>

      <div className="flex flex-col items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          onChange={handleFileChange}
          disabled={disabled || uploading}
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={disabled || uploading}
          className="inline-flex items-center gap-2 rounded border border-line bg-panel px-4 py-2 text-sm font-medium text-ink transition hover:border-accent hover:bg-panelSoft disabled:cursor-not-allowed disabled:opacity-60"
        >
          <FileUp className="h-4 w-4" aria-hidden="true" />
          Select file
        </button>
        {error && <p className="max-w-2xl text-center text-sm text-danger">{error}</p>}
      </div>
    </section>
  );
}

export default UploadPanel;
