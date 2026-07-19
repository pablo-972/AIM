import { useEffect, useState } from "react";

export function useElapsedTime(
  startedAt: string | undefined,
  active: boolean,
): number {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!active || !startedAt) {
      setElapsedSeconds(0);
      return;
    }

    const startedAtMs = Date.parse(startedAt);
    const tick = () => {
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startedAtMs) / 1000)));
    };

    tick();
    const interval = window.setInterval(tick, 1000);
    return () => window.clearInterval(interval);
  }, [active, startedAt]);

  return elapsedSeconds;
}
