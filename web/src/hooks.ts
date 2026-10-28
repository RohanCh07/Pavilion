import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type RefObject } from "react";
import { useRefreshNonce } from "./refresh";

// --- Routing: hash based ("#/series/12"), so any static host or the API can serve the app.

function subscribeHash(cb: () => void) {
  window.addEventListener("hashchange", cb);
  return () => window.removeEventListener("hashchange", cb);
}

export function useRoute(): { path: string[]; query: URLSearchParams } {
  const hash = useSyncExternalStore(subscribeHash, () => window.location.hash);
  const [rawPath, rawQuery = ""] = hash.replace(/^#/, "").split("?");
  return {
    path: rawPath.split("/").filter(Boolean),
    query: new URLSearchParams(rawQuery),
  };
}

export function navigate(to: string, replace = false) {
  const url = `#${to}`;
  if (replace) window.location.replace(url);
  else window.location.hash = to;
  window.scrollTo({ top: 0 });
}

export function back(fallback = "/") {
  if (window.history.length > 1) window.history.back();
  else navigate(fallback, true);
}

// --- Data loading, refreshed only when the user taps Refresh.

interface DataState<T> {
  data: T | undefined;
  error: string | null;
  loading: boolean;
  reload: (fresh?: boolean) => void;
}

export function useData<T>(
  load: (fresh: boolean) => Promise<T>,
  deps: unknown[],
  options: { initial?: T } = {},
): DataState<T> {
  const [data, setData] = useState<T | undefined>(options.initial);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(options.initial === undefined);
  const loadRef = useRef(load);
  loadRef.current = load;
  const seq = useRef(0);

  const run = useCallback((fresh = false) => {
    const id = ++seq.current;
    setLoading((was) => was || !fresh);
    loadRef
      .current(fresh)
      .then((value) => {
        if (id !== seq.current) return;
        setData(value);
        setError(null);
      })
      .catch((err: Error) => {
        if (id === seq.current) setError(err.message);
      })
      .finally(() => {
        if (id === seq.current) setLoading(false);
      });
  }, []);

  useEffect(() => {
    run(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  // Nothing reloads on its own: the Refresh button (refresh.ts) re-runs every loader on screen.
  const nonce = useRefreshNonce();
  const firstNonce = useRef(nonce);
  useEffect(() => {
    if (nonce !== firstNonce.current) run(true);
  }, [nonce, run]);

  return { data, error, loading, reload: run };
}


/** True once the element has scrolled near the viewport (stays true). Used to defer requests. */
export function useInView<T extends Element>(ref: RefObject<T | null>, margin = "200px"): boolean {
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return;
    if (!("IntersectionObserver" in window)) return setSeen(true);
    const io = new IntersectionObserver((entries) => entries.some((e) => e.isIntersecting) && setSeen(true), {
      rootMargin: margin,
    });
    io.observe(el);
    return () => io.disconnect();
  }, [ref, seen, margin]);
  return seen;
}
