"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function readStoredTheme(): Theme {
  if (document.documentElement.classList.contains("dark")) return "dark";
  return "light";
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    // Read the real theme only after mount -- the server has no access to the
    // .dark class the inline init script (layout.tsx) sets before hydration,
    // so the client's first render must start from the same `null` placeholder.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTheme(readStoredTheme());
  }, []);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.classList.toggle("dark", next === "dark");
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Private browsing / blocked storage -- theme just won't persist.
    }
  }

  return (
    <button
      onClick={toggle}
      type="button"
      aria-label="Toggle dark mode"
      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-zinc-300 text-lg leading-none transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
    >
      {theme === null ? "" : theme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}
