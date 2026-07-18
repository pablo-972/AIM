import { ChangeEvent, FormEvent, useRef, useState } from "react";
import { FileUp, FolderOpen, Moon, Search, Sun, X } from "lucide-react";
import ExistingAnalysesPanel from "../analysis/ExistingAnalysesPanel";
import LogoMark from "./LogoMark";
import type { AnalysisStatusPayload } from "../../types";

type NavbarProps = {
  darkMode: boolean;
  existingDisabled: boolean;
  selectedAnalysisId: string | null;
  searching: boolean;
  uploading: boolean;
  onSelectExisting: (analysis: AnalysisStatusPayload) => void;
  onSearch: (value: string) => void;
  onUpload: (file: File) => void;
  onToggleTheme: () => void;
};

function Navbar({
  darkMode,
  existingDisabled,
  selectedAnalysisId,
  searching,
  uploading,
  onSelectExisting,
  onSearch,
  onUpload,
  onToggleTheme,
}: NavbarProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [query, setQuery] = useState("");
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const [existingOpen, setExistingOpen] = useState(false);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSearch(query);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onUpload(file);
    }
    event.target.value = "";
  };

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-panel/95 backdrop-blur">
      <div className="mx-auto grid h-16 w-full max-w-7xl grid-cols-[1fr_auto_1fr] items-center gap-3 px-4 sm:grid-cols-[auto_1fr_auto] sm:px-6 lg:px-8">
        <a
          href="/"
          className="col-start-1 hidden min-w-0 items-center justify-self-start sm:flex"
          aria-label="AIM home"
        >
          <LogoMark />
        </a>

        <a
          href="/"
          className="col-start-2 row-start-1 flex items-center justify-self-center sm:hidden"
          aria-label="AIM home"
        >
          <LogoMark />
        </a>

        <form
          onSubmit={submit}
          className="col-start-2 hidden w-full max-w-2xl justify-self-center sm:block"
        >
          <SearchBox
            query={query}
            searching={searching}
            onQueryChange={setQuery}
          />
        </form>

        <div className="relative col-start-3 row-start-1 flex items-center justify-self-end">
          <button
            type="button"
            onClick={() => setMobileSearchOpen(true)}
            className="inline-flex h-10 w-10 items-center justify-center rounded border border-transparent text-muted transition hover:border-line hover:bg-panelSoft hover:text-ink sm:hidden"
            aria-label="Search by hash"
          >
            <Search className="h-5 w-5" aria-hidden="true" />
          </button>

          <input
            ref={inputRef}
            type="file"
            className="hidden"
            onChange={handleFileChange}
            disabled={uploading}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="inline-flex h-10 w-10 items-center justify-center rounded border border-transparent text-muted transition hover:border-line hover:bg-panelSoft hover:text-ink disabled:cursor-not-allowed disabled:opacity-60"
            aria-label="Upload file"
            title="Upload file"
          >
            <FileUp className="h-5 w-5" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={() => setExistingOpen((current) => !current)}
            className="inline-flex h-10 w-10 items-center justify-center rounded border border-transparent text-muted transition hover:border-line hover:bg-panelSoft hover:text-ink"
            aria-label="Existing samples"
            title="Existing samples"
          >
            <FolderOpen className="h-5 w-5" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={onToggleTheme}
            className="inline-flex h-10 w-10 items-center justify-center rounded border border-transparent text-muted transition hover:border-line hover:bg-panelSoft hover:text-ink"
            aria-label={darkMode ? "Use light mode" : "Use dark mode"}
            title={darkMode ? "Use light mode" : "Use dark mode"}
          >
            {darkMode ? (
              <Sun className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Moon className="h-5 w-5" aria-hidden="true" />
            )}
          </button>

          {existingOpen && (
            <div className="absolute right-0 top-12 z-50 max-h-[70vh] w-[min(92vw,48rem)] overflow-y-auto rounded-md shadow-xl">
              <ExistingAnalysesPanel
                disabled={existingDisabled}
                selectedAnalysisId={selectedAnalysisId}
                onSelect={(analysis) => {
                  setExistingOpen(false);
                  onSelectExisting(analysis);
                }}
              />
            </div>
          )}
        </div>
      </div>

      {mobileSearchOpen && (
        <div className="border-t border-line bg-panel p-3 sm:hidden">
          <form onSubmit={submit} className="flex items-center gap-2">
            <SearchBox
              query={query}
              searching={searching}
              onQueryChange={setQuery}
            />
            <button
              type="button"
              onClick={() => setMobileSearchOpen(false)}
              className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded border border-line bg-panelSoft text-muted"
              aria-label="Close search"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
          </form>
        </div>
      )}
    </header>
  );
}

type SearchBoxProps = {
  query: string;
  searching: boolean;
  onQueryChange: (value: string) => void;
};

function SearchBox({ query, searching, onQueryChange }: SearchBoxProps) {
  return (
    <label className="flex h-10 w-full items-center gap-2 rounded border border-line bg-panelSoft px-3 text-sm text-ink shadow-sm focus-within:border-pink-500">
      <Search className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
      <input
        type="search"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        placeholder="Search SHA256"
        className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted"
        disabled={searching}
      />
    </label>
  );
}

export default Navbar;
