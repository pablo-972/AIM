import { analysisTabs } from "../../types";
import type { AnalysisTab } from "../../types";

type AnalysisTabsProps = {
  activeTab: AnalysisTab;
  onTabChange: (tab: AnalysisTab) => void;
};

function AnalysisTabs({ activeTab, onTabChange }: AnalysisTabsProps) {
  return (
    <nav className="flex flex-wrap gap-2 rounded-md border border-line bg-panel p-2">
      {analysisTabs.map((tab) => (
        <button
          key={tab}
          type="button"
          onClick={() => onTabChange(tab)}
          className={`rounded px-3 py-2 text-sm font-medium transition ${
            activeTab === tab
              ? "bg-pink-500 text-white"
              : "text-muted hover:bg-panelSoft hover:text-ink"
          }`}
        >
          {tab}
        </button>
      ))}
    </nav>
  );
}

export default AnalysisTabs;
