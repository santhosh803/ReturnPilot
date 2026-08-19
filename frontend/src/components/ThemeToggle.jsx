import React, { useCallback, useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";

const STORAGE_KEY = "theme";

function getCurrentTheme() {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.classList.contains("light") ? "light" : "dark";
}

// Apply a theme to the document. `persist` writes to localStorage, which also
// notifies other tabs via the "storage" event (that event does NOT fire in the
// tab that made the change, so there is no feedback loop).
function applyTheme(theme, persist = true) {
  const root = document.documentElement;
  root.classList.toggle("light", theme === "light");
  root.style.colorScheme = theme;
  if (persist) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      /* ignore storage errors (private mode, etc.) */
    }
  }
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState(getCurrentTheme);

  // Cross-tab sync: mirror theme changes made in other tabs.
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === STORAGE_KEY && e.newValue && e.newValue !== getCurrentTheme()) {
        applyTheme(e.newValue, false);
        setTheme(e.newValue);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const toggle = useCallback(
    (event) => {
      const next = theme === "dark" ? "light" : "dark";
      const commit = () => {
        applyTheme(next);
        setTheme(next);
      };

      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      // Fall back to an instant switch where View Transitions aren't supported.
      if (!document.startViewTransition || reduceMotion) {
        commit();
        return;
      }

      // Circular reveal originating from the toggle's click point.
      const x = event.clientX;
      const y = event.clientY;
      const endRadius = Math.hypot(
        Math.max(x, window.innerWidth - x),
        Math.max(y, window.innerHeight - y)
      );

      const transition = document.startViewTransition(commit);
      transition.ready.then(() => {
        document.documentElement.animate(
          {
            clipPath: [
              `circle(0px at ${x}px ${y}px)`,
              `circle(${endRadius}px at ${x}px ${y}px)`,
            ],
          },
          {
            duration: 450,
            easing: "ease-in-out",
            pseudoElement: "::view-transition-new(root)",
          }
        );
      });
    },
    [theme]
  );

  const isDark = theme === "dark";
  return (
    <button
      onClick={toggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="w-9 h-9 rounded-xl flex items-center justify-center text-slate-400 hover:text-slate-100 hover:bg-slate-800/70 border border-slate-800 transition-colors cursor-pointer"
    >
      {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
    </button>
  );
}
