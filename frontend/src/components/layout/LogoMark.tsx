import { useState } from "react";

type LogoMarkProps = {
  size?: "sm" | "lg";
  showName?: boolean;
};

function LogoMark({ size = "sm", showName = true }: LogoMarkProps) {
  const boxSize = size === "lg" ? "h-16 w-16 sm:h-20 sm:w-20" : "h-9 w-9";
  const textSize = size === "lg" ? "text-5xl sm:text-6xl" : "text-lg";

  return (
    <div className="flex items-center gap-3">
      <div
        className={`${boxSize} shrink-0 bg-pink-500`}
        style={{
          mask: "url('/logo.svg') center / contain no-repeat",
          WebkitMask: "url('/logo.svg') center / contain no-repeat",
        }}
      />

      {showName && (
        <span className={`${textSize} font-semibold text-pink-500`}>
          AIM
        </span>
      )}
    </div>
  );
}

export default LogoMark;

