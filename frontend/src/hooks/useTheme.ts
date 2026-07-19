import { useCallback, useEffect, useState } from "react";

type UseThemeResult = {
  darkMode: boolean;
  toggleDarkMode: () => void;
};

const THEME_STORAGE_KEY = "aim-theme";

function prefersDarkMode(): boolean {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? true;
}

function initialDarkMode(): boolean {
  const storedTheme = readStoredTheme();
  if (storedTheme === "dark") {
    return true;
  }
  if (storedTheme === "light") {
    return false;
  }

  return prefersDarkMode();
}

function readStoredTheme(): string | null {
  try {
    return window.localStorage.getItem(THEME_STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStoredTheme(darkMode: boolean): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, darkMode ? "dark" : "light");
  } catch {
    return;
  }
}

export function useTheme(): UseThemeResult {
  const [darkMode, setDarkMode] = useState(() => initialDarkMode());

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  const toggleDarkMode = useCallback(() => {
    setDarkMode((current) => {
      const next = !current;
      writeStoredTheme(next);
      return next;
    });
  }, []);

  return {
    darkMode,
    toggleDarkMode,
  };
}
