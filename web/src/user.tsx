// Who is using this browser. Until real login exists, the user picks a name once and it's
// sent to the API as X-User-Id. Anyone using the same name shares the same teams.
import { useState, useSyncExternalStore, type FormEvent, type ReactNode } from "react";
import { setApiUser } from "./api";

const KEY = "pavilion-user";
const listeners = new Set<() => void>();

function read(): string {
  try {
    return localStorage.getItem(KEY) ?? "";
  } catch {
    return memory;
  }
}
let memory = "";

function write(name: string) {
  memory = name;
  try {
    if (name) localStorage.setItem(KEY, name);
    else localStorage.removeItem(KEY);
  } catch {
    /* private mode: keep it for this visit only */
  }
  setApiUser(name);
  listeners.forEach((l) => l());
}

setApiUser(read());

export function useUser(): string {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    read,
  );
}

export function forgetUser() {
  write("");
}

export function UserGate({ children }: { children: ReactNode }) {
  const user = useUser();
  const [name, setName] = useState("");
  if (user) return <>{children}</>;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const clean = name.trim().replace(/\s+/g, " ");
    if (clean) write(clean.slice(0, 40));
  };

  return (
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-surface px-gutter font-body-md text-body-md text-on-surface antialiased">
      <div className="pointer-events-none absolute -top-16 -right-16 h-72 w-72 rounded-full bg-primary-fixed/30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -left-10 h-60 w-60 rounded-full bg-secondary-fixed/40 blur-2xl" />
      <form onSubmit={submit} className="relative z-10 w-full max-w-sm rounded-2xl bg-surface-container-lowest p-space-xl shadow-sm">
        <div className="mb-space-lg flex items-center gap-space-sm">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-[#0b1c30] text-primary-container">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
              <path d="M5 5h14M7.5 5v14M12 5v14M16.5 5v14" />
            </svg>
          </span>
          <span className="font-headline-md text-headline-md font-bold tracking-tight">Pavilion</span>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-container px-space-xs py-space-2xs font-label-badge text-label-badge text-primary">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary-container" />
          FANTASY CRICKET
        </span>
        <h1 className="mt-space-sm font-headline-lg-mobile text-headline-lg-mobile font-bold tracking-tight">Welcome to Pavilion</h1>
        <p className="mt-space-2xs mb-space-lg font-body-md text-body-md text-on-surface-variant">
          Pick a name to save your teams under. Use the same name on any device to see them.
        </p>
        <label className="mb-space-xs block font-label-meta text-label-meta font-semibold tracking-wider text-outline uppercase" htmlFor="name">
          Your name
        </label>
        <input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
          autoComplete="nickname"
          maxLength={40}
          placeholder="e.g. Rohan"
          className="w-full rounded-lg bg-surface-container-low px-space-md py-space-sm font-body-md text-body-md text-on-surface placeholder:text-outline focus:ring-2 focus:ring-primary-container focus:outline-none"
        />
        <button
          disabled={!name.trim()}
          className="mt-space-lg flex w-full items-center justify-center gap-1.5 rounded-lg bg-primary-container px-space-lg py-space-sm font-body-md text-body-md font-semibold text-on-primary-container shadow-sm transition-all hover:bg-primary hover:text-on-primary disabled:opacity-50"
        >
          Continue
        </button>
      </form>
    </div>
  );
}
