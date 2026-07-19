import UploadPanel from "../analysis/UploadPanel";
import LogoMark from "../layout/LogoMark";
import type { AnalysisStatusPayload } from "../../types";

type HomeViewProps = {
  disabled: boolean;
  onAnalysisCreated: (status: AnalysisStatusPayload) => void;
};

function HomeView({ disabled, onAnalysisCreated }: HomeViewProps) {
  return (
    <>
      <section className="flex flex-col items-center justify-center gap-6 py-8 text-center sm:py-12">
        <div className="flex items-center gap-5">
          <LogoMark size="lg" showName={false} />
          <h1 className="text-5xl font-semibold tracking-normal text-pink-500 sm:text-7xl">
            AIM
          </h1>
        </div>
        <p className="max-w-3xl text-base leading-7 text-muted sm:text-lg">
          Analyze binaries using a traditional malware analysis workflow enhanced with AI-powered behavioral inference, 
          iterative context enrichment, an autonomous reverse engineering agent, and comprehensive technical report generation.
        </p>
      </section>

      <UploadPanel
        disabled={disabled}
        onAnalysisCreated={onAnalysisCreated}
      />
    </>
  );
}

export default HomeView;
