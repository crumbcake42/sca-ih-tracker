import { useSyncExternalStore } from "react";

export type Theme = "light" | "dark" | "auto";

const STORAGE_KEY = "theme";
const listeners = new Set<() => void>();

function getStoredTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "auto")
      return stored;
  } catch {
    // localStorage unavailable
  }
  return "auto";
}

export function getResolvedTheme(): "light" | "dark" {
  const stored = getStoredTheme();
  if (stored !== "auto") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function setTheme(value: Theme): void {
  try {
    localStorage.setItem(STORAGE_KEY, value);
  } catch {
    // localStorage unavailable
  }
  const resolved =
    value === "auto"
      ? window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      : value;
  const root = document.documentElement;
  root.classList.remove("light", "dark");
  root.classList.add(resolved);
  root.style.colorScheme = resolved;
  listeners.forEach((fn) => fn());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Returns [storedTheme, setTheme] — storedTheme is "auto" | "light" | "dark". */
export function useTheme(): [Theme, (value: Theme) => void] {
  const theme = useSyncExternalStore(
    subscribe,
    getStoredTheme,
    (): Theme => "auto",
  );
  return [theme, setTheme];
}
