import { useCallback, useEffect, useState } from "react";

type UseThemeResult = {
  darkMode: boolean;
  toggleDarkMode: () => void;
};

function prefersDarkMode(): boolean {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? true;
}

export function useTheme(): UseThemeResult {
  const [darkMode, setDarkMode] = useState(() => prefersDarkMode());

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  const toggleDarkMode = useCallback(() => {
    setDarkMode((current) => !current);
  }, []);

  return {
    darkMode,
    toggleDarkMode,
  };
}
