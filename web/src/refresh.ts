// Manual refresh: nothing reloads on its own. The Refresh button reloads every loader on the
// current screen with fresh data, at most once a minute (the cooldown survives page reloads).
import { useEffect, useState, useSyncExternalStore } from "react";
import { clearCache } from "./api";

export const COOLDOWN_MS = 60_000;
const KEY = "pavilion-last-refresh";

let nonce = 0;
const listeners = new Set<() => void>();

function lastRefresh(): number {
  try {
    return Number(localStorage.getItem(KEY)) || 0;
  } catch {
    return memoryLast;
  }
}
let memoryLast = 0;

export function cooldownLeft(now = Date.now()): number {
  return Math.max(0, lastRefresh() + COOLDOWN_MS - now);
}

/** Reload everything on screen with fresh data. Returns false while cooling down. */
export function requestRefresh(): boolean {
  if (cooldownLeft() > 0) return false;
  memoryLast = Date.now();
  try {
    localStorage.setItem(KEY, String(memoryLast));
  } catch {
    /* private mode: the cooldown just lasts for this visit */
  }
  clearCache();
  nonce++;
  listeners.forEach((l) => l());
  return true;
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

/** Changes every time the user refreshes; loaders re-run when it does. */
export function useRefreshNonce(): number {
  return useSyncExternalStore(subscribe, () => nonce);
}

/** Seconds of cooldown left, ticking down once a second while above zero. */
export function useCooldown(): number {
  const nonceNow = useRefreshNonce();
  const [left, setLeft] = useState(() => Math.ceil(cooldownLeft() / 1000));
  useEffect(() => {
    setLeft(Math.ceil(cooldownLeft() / 1000));
    const timer = window.setInterval(() => {
      const s = Math.ceil(cooldownLeft() / 1000);
      setLeft(s);
      if (s <= 0) window.clearInterval(timer);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [nonceNow]);
  return left;
}
