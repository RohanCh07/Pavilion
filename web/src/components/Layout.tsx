import type { ReactNode } from "react";
import { initials } from "../format";
import { navigate } from "../hooks";
import { forgetUser, useUser } from "../user";
import { Icon } from "./Icon";
import { RefreshButton } from "./RefreshButton";

export type NavKey = "series" | "matches" | "teams" | "pools" | "leaderboard" | "rules";

// Sidebar (desktop) and bottom bar (phone) entries, as in the design.
const SIDEBAR: { key: NavKey; label: string; icon: string; to: string }[] = [
  { key: "series", label: "Series", icon: "home", to: "/" },
  { key: "teams", label: "My Teams", icon: "emoji_events", to: "/teams" },
  { key: "pools", label: "Pools", icon: "groups", to: "/pools" },
  { key: "matches", label: "Match Center", icon: "schedule", to: "/matches" },
  { key: "leaderboard", label: "Leaderboard", icon: "leaderboard", to: "/leaderboards" },
  { key: "rules", label: "Rules & Scoring", icon: "menu_book", to: "/rules" },
];
const BOTTOM: { key: NavKey; label: string; icon: string; to: string }[] = [
  { key: "series", label: "Series", icon: "home", to: "/" },
  { key: "matches", label: "Matches", icon: "sports_cricket", to: "/matches" },
  { key: "pools", label: "Pools", icon: "groups", to: "/pools" },
  { key: "teams", label: "My Teams", icon: "emoji_events", to: "/teams" },
];

export function Logo({ small = false }: { small?: boolean }) {
  return (
    <span
      className={`inline-flex items-center justify-center rounded-lg bg-[#0b1c30] text-primary-container ${
        small ? "h-8 w-8" : "h-8 w-8"
      }`}
      aria-hidden="true"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
        <path d="M5 5h14M7.5 5v14M12 5v14M16.5 5v14" />
      </svg>
    </span>
  );
}

function Avatar({ name }: { name: string }) {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary-container font-label-badge text-label-badge text-on-secondary-fixed">
      {initials(name || "?")}
    </span>
  );
}

export function Layout({
  active,
  teamCount,
  children,
}: {
  active: NavKey | null;
  teamCount?: number;
  children: ReactNode;
}) {
  const user = useUser();
  const switchUser = () => {
    if (confirm(`Signed in as ${user}. Switch user?`)) forgetUser();
  };

  return (
    <div className="min-h-dvh bg-surface font-body-md text-body-md text-on-surface antialiased">
      {/* Desktop sidebar */}
      <aside className="fixed top-0 left-0 z-40 hidden h-screen w-60 flex-col justify-between bg-surface-container-lowest shadow-[0_1px_8px_rgba(0,0,0,0.04)] lg:flex">
        <div className="flex flex-col">
          <div className="flex h-16 items-center justify-between px-space-lg">
            <a href="#/" className="flex items-center gap-space-sm">
              <Logo />
              <span className="font-headline-md text-headline-md font-bold tracking-tight text-on-surface">
                Pavilion
              </span>
            </a>
            <span className="rounded bg-surface-container-low px-space-xs py-space-2xs font-label-badge text-label-badge font-bold tracking-wider text-primary uppercase">
              Beta
            </span>
          </div>
          <div className="px-space-lg py-space-xs">
            <p className="mb-space-xs font-label-meta text-label-meta font-semibold tracking-wider text-outline uppercase">
              Navigation
            </p>
          </div>
          <nav className="flex flex-col gap-space-2xs px-space-sm">
            {SIDEBAR.map((item) => {
              const on = item.key === active;
              return (
                <a
                  key={item.key}
                  href={`#${item.to}`}
                  aria-current={on ? "page" : undefined}
                  className={`flex items-center justify-between rounded-lg px-space-md py-space-sm transition-colors ${
                    on
                      ? "bg-primary-container font-semibold text-on-primary-container"
                      : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                  }`}
                >
                  <div className="flex items-center gap-space-sm">
                    <Icon name={item.icon} className="text-[20px]" />
                    <span>{item.label}</span>
                  </div>
                  {item.key === "teams" && !!teamCount && (
                    <span className="rounded-full bg-secondary-container px-space-xs py-space-2xs font-label-numeric text-label-numeric font-medium text-on-secondary-container">
                      {teamCount}
                    </span>
                  )}
                  {item.key === "matches" && (
                    <span className="relative flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary-container opacity-75" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                    </span>
                  )}
                </a>
              );
            })}
          </nav>
        </div>
        <div className="m-space-sm flex flex-col gap-space-xs rounded-xl bg-surface-container-low/50 p-space-sm">
          <div className="flex items-center justify-between px-space-sm py-space-2xs">
            <div className="flex items-center gap-space-2xs font-label-meta text-label-meta text-outline">
              <span className="h-1.5 w-1.5 rounded-full bg-primary-container" />
              <span>Live data · CREX</span>
            </div>
          </div>
          <button
            onClick={switchUser}
            className="flex cursor-pointer items-center gap-space-sm rounded-lg px-space-sm py-space-xs text-left transition-colors hover:bg-surface-container-lowest"
          >
            <Avatar name={user} />
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="truncate font-body-sm text-body-sm font-semibold text-on-surface">{user}</span>
              <span className="font-label-numeric text-label-numeric text-outline">Switch user</span>
            </div>
            <Icon name="unfold_more" className="text-[18px] text-outline" />
          </button>
        </div>
      </aside>

      <div className="flex min-h-screen flex-col lg:pl-60">
        {/* Top bar */}
        <header className="fixed top-0 right-0 left-0 z-30 h-16 bg-surface-container-lowest/85 px-gutter shadow-[0_1px_8px_rgba(0,0,0,0.04)] backdrop-blur-xl lg:left-60 lg:px-gutter-desktop">
          <div className="flex h-16 w-full items-center justify-between gap-space-md">
            <a href="#/" className="flex items-center gap-space-sm lg:hidden">
              <Logo />
              <span className="font-headline-md text-headline-md font-bold tracking-tight text-on-surface">
                Pavilion
              </span>
              <span className="rounded bg-surface-container-low px-space-xs py-space-2xs font-label-badge text-label-badge font-bold text-primary">
                LIVE
              </span>
            </a>
            <div className="hidden max-w-md flex-1 items-center md:flex">
              <button
                onClick={() => navigate("/")}
                className="relative flex w-full items-center rounded-lg bg-surface-container-low py-space-xs pr-4 pl-9 text-left font-body-sm text-body-sm text-outline"
              >
                <Icon name="search" className="pointer-events-none absolute left-3 text-[18px] text-outline" />
                Search series, matches, players...
              </button>
            </div>
            <div className="flex items-center gap-space-sm">
              <RefreshButton />
              <button
                onClick={() => navigate("/")}
                className="hidden items-center gap-space-xs rounded-lg bg-primary-container px-space-md py-space-xs font-body-sm text-body-sm font-semibold text-on-primary-container transition-colors hover:bg-primary hover:text-on-primary sm:inline-flex"
              >
                <Icon name="add" className="text-[18px]" />
                <span>Create Team</span>
              </button>
              <button
                onClick={() => navigate("/matches")}
                aria-label="Live matches"
                className="relative hidden rounded-lg p-space-xs text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface sm:block"
              >
                <Icon name="notifications" className="text-[20px]" />
                <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-error" />
              </button>
              <button onClick={switchUser} className="flex items-center lg:hidden" aria-label="Account">
                <Avatar name={user} />
              </button>
            </div>
          </div>
        </header>

        <main className="w-full bg-surface px-gutter pt-16 pb-24 lg:px-gutter-desktop lg:pb-space-xl">
          <div className="pt-space-lg lg:pt-space-xl">{children}</div>
        </main>
      </div>

      {/* Phone bottom navigation */}
      <nav className="pb-safe fixed right-0 bottom-0 left-0 z-50 bg-surface-container-lowest/90 shadow-[0_-1px_8px_rgba(0,0,0,0.04)] backdrop-blur-xl lg:hidden">
        <div className="flex h-16 items-center justify-around px-space-sm">
          {BOTTOM.map((item) => {
            const on = item.key === active;
            return (
              <a
                key={item.key}
                href={`#${item.to}`}
                aria-current={on ? "page" : undefined}
                className={`relative flex min-w-16 flex-col items-center justify-center rounded-lg px-space-sm py-space-2xs ${
                  on ? "font-semibold text-primary-container" : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                <Icon name={item.icon} className="text-[22px]" />
                <span className="font-label-meta text-label-meta">{item.label}</span>
                {item.key === "teams" && !!teamCount && (
                  <span className="absolute top-1 right-3 h-1.5 w-1.5 rounded-full bg-primary-container" />
                )}
              </a>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
