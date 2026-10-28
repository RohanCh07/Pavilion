// Small building blocks, each copied from a repeated pattern in the Stitch screens.
import type { ReactNode } from "react";
import type { MatchStatus, Position, Role } from "../api";
import { ROLE_SHORT } from "../format";
import { back } from "../hooks";
import { Icon } from "./Icon";

export const card = "bg-surface-container-lowest rounded-2xl shadow-sm";
export const btnPrimary =
  "inline-flex items-center justify-center gap-space-xs rounded-lg bg-primary-container px-space-md py-space-xs font-body-sm text-body-sm font-semibold text-on-primary-container shadow-sm transition-all hover:bg-primary hover:text-on-primary active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50";
export const btnSoft =
  "inline-flex items-center justify-center gap-space-2xs rounded-lg bg-surface-container px-space-md py-space-xs font-body-sm text-body-sm font-semibold text-on-surface transition-colors hover:bg-surface-container-high disabled:pointer-events-none disabled:opacity-60";
export const btnLow =
  "inline-flex items-center justify-center gap-space-2xs rounded-lg bg-surface-container-low px-space-md py-space-xs font-body-sm text-body-sm font-medium text-on-surface transition-all hover:bg-surface-container disabled:pointer-events-none disabled:opacity-60";

/** "LIVE NOW" style pill with a pinging dot. */
export function LivePill({ label = "Live", soft = false }: { label?: string; soft?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-space-xs py-space-2xs font-label-badge text-label-badge uppercase ${
        soft ? "bg-primary-container/15 text-primary" : "bg-surface-container text-primary"
      }`}
    >
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary-container opacity-75" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
      </span>
      {label}
    </span>
  );
}

export function MatchStatusTag({ status, upcomingLabel }: { status: MatchStatus; upcomingLabel?: string }) {
  if (status === "LIVE") return <LivePill label="Live coverage" soft />;
  if (status === "FT")
    return (
      <span className="rounded bg-surface-container-low px-space-xs py-space-2xs font-label-badge text-label-badge font-bold text-outline uppercase">
        Concluded
      </span>
    );
  return (
    <span className="inline-flex items-center gap-space-2xs rounded bg-tertiary-fixed px-space-xs py-space-2xs font-label-numeric text-label-numeric font-semibold text-on-tertiary-fixed">
      <Icon name="timer" className="text-[15px]" />
      {upcomingLabel ?? "Upcoming"}
    </span>
  );
}

/** Short side code for team circles: "New Zealand" -> NZ, "India" -> IND. */
export function sideCode(name: string): string {
  const words = name.replace(/[^A-Za-z ]/g, " ").trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 3).toUpperCase();
  return words
    .slice(0, 3)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

export function TeamCircle({ name, size = "sm" }: { name: string; size?: "sm" | "lg" }) {
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full bg-secondary-fixed font-label-badge font-bold text-on-secondary-fixed ${
        size === "lg" ? "h-10 w-10 text-[12px]" : "h-6 min-w-6 px-1 text-[9px]"
      }`}
      title={name}
    >
      {sideCode(name)}
    </span>
  );
}

export function RoleBadge({ position }: { position: Position }) {
  return (
    <span className="rounded bg-surface-container-high px-1.5 py-0.5 font-label-badge text-label-badge font-bold text-on-surface-variant">
      {ROLE_SHORT[position]}
    </span>
  );
}

/** The design's C / VC circles (28px). */
export function MultiplierButton({
  kind,
  active,
  disabled,
  onClick,
}: {
  kind: "C" | "VC";
  active: boolean;
  disabled?: boolean;
  onClick?: () => void;
}) {
  const on = kind === "C" ? "bg-on-surface text-surface" : "bg-secondary text-surface";
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      aria-pressed={active}
      aria-label={kind === "C" ? "Make captain (2x)" : "Make vice-captain (1.5x)"}
      className={`flex h-9 w-9 items-center justify-center rounded-full font-label-badge text-[10px] font-bold transition-transform active:scale-95 md:h-7 md:w-7 ${
        active
          ? `${on} ring-2 ring-primary-container`
          : disabled
            ? "cursor-not-allowed bg-surface-container-high text-outline opacity-50"
            : "bg-surface-container-high text-outline hover:text-on-surface"
      }`}
    >
      {kind}
    </button>
  );
}

/** Small round C / VC marker used next to names. */
export function RoleDot({ role }: { role: Role }) {
  if (role === "player") return null;
  return (
    <span
      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full font-label-badge text-[9px] font-bold ${
        role === "captain" ? "bg-tertiary text-on-tertiary" : "bg-secondary text-on-secondary"
      }`}
    >
      {role === "captain" ? "C" : "VC"}
    </span>
  );
}

/** Segmented control (series tabs, my-teams tabs, team filter). */
export function Segmented<T extends string | number>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: ReactNode; count?: number; dot?: boolean }[];
}) {
  return (
    <div className="no-scrollbar -mx-gutter overflow-x-auto px-gutter lg:mx-0 lg:px-0">
      <div className="inline-flex items-center gap-space-xs rounded-xl bg-surface-container-low p-space-2xs" role="tablist">
        {options.map((o) => {
          const on = o.value === value;
          return (
            <button
              key={String(o.value)}
              type="button"
              role="tab"
              aria-selected={on}
              onClick={() => onChange(o.value)}
              className={`flex shrink-0 items-center gap-space-xs rounded-lg px-space-md py-space-xs font-body-sm text-body-sm whitespace-nowrap transition-all ${
                on
                  ? "bg-surface-container-lowest font-semibold text-on-surface shadow-sm"
                  : "font-medium text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {o.dot && <span className="inline-block h-2 w-2 rounded-full bg-primary-container" />}
              <span>{o.label}</span>
              {o.count !== undefined && (
                <span
                  className={`rounded-full px-space-xs py-space-2xs font-label-numeric text-[11px] ${
                    on ? "bg-primary-container/20 text-on-primary-container" : "bg-surface-container"
                  }`}
                >
                  {o.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** Rounded-full uppercase filter chips (series page match filter). */
export function FilterChips<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="no-scrollbar flex items-center gap-space-xs overflow-x-auto pb-space-2xs sm:pb-0">
      <span className="hidden font-label-meta text-label-meta tracking-wider text-outline uppercase md:inline">
        Filter:
      </span>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={`shrink-0 rounded-full px-space-sm py-space-2xs font-label-badge text-label-badge font-semibold whitespace-nowrap ${
            o.value === value
              ? "bg-primary text-on-primary"
              : "bg-surface-container-lowest text-on-surface-variant hover:text-on-surface"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function SearchBox({
  value,
  onChange,
  placeholder,
  white = false,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  white?: boolean;
}) {
  return (
    <div className="relative flex-1">
      <Icon
        name="search"
        className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-[18px] text-outline"
      />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        enterKeyHint="search"
        className={`w-full rounded-lg border-0 py-space-xs pr-3 pl-9 font-body-sm text-body-sm text-on-surface placeholder:text-outline focus:ring-2 focus:ring-primary-container focus:outline-none ${
          white ? "bg-surface-container-lowest shadow-sm" : "bg-surface-container-low"
        }`}
        style={{ minHeight: 36 }}
      />
    </div>
  );
}

export function Breadcrumb({ backTo, label, current }: { backTo: string; label: string; current: string }) {
  return (
    <nav className="flex min-w-0 items-center gap-space-xs font-label-meta text-label-meta text-outline">
      <button
        type="button"
        onClick={() => back(backTo)}
        className="flex shrink-0 items-center gap-space-2xs py-1 transition-colors hover:text-primary"
      >
        <Icon name="arrow_back" className="text-[15px]" />
        <span>{label}</span>
      </button>
      <span className="text-outline-variant">/</span>
      <span className="truncate font-semibold text-on-surface">{current}</span>
    </nav>
  );
}

export function Skeletons({ rows = 3, height = 160 }: { rows?: number; height?: number }) {
  return (
    <div className="flex flex-col gap-space-lg" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton rounded-2xl" style={{ height }} />
      ))}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className={`${card} flex flex-col items-center gap-space-sm p-space-xl text-center`}>
      <Icon name="cloud_off" className="text-[28px] text-outline" />
      <p className="font-body-md text-body-md text-on-surface-variant">{message}</p>
      {onRetry && (
        <button type="button" className={btnSoft} onClick={onRetry}>
          <Icon name="refresh" className="text-[16px]" /> Try again
        </button>
      )}
    </div>
  );
}

/** The design's "Available Fantasy Leagues" style panel, reused for empty states. */
export function EmptyPanel({
  icon = "sports_cricket",
  title,
  text,
  action,
}: {
  icon?: string;
  title: string;
  text?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex w-full flex-col items-center justify-between gap-space-lg rounded-2xl bg-surface-container-low p-space-lg md:flex-row lg:p-space-xl">
      <div className="flex items-center gap-space-lg">
        <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-surface-container-highest text-primary">
          <Icon name={icon} className="text-[36px]" />
        </div>
        <div className="flex flex-col">
          <h4 className="font-headline-md text-headline-md font-bold text-on-surface">{title}</h4>
          {text && <p className="mt-1 font-body-md text-body-md text-on-surface-variant">{text}</p>}
        </div>
      </div>
      {action && <div className="flex w-full shrink-0 justify-end md:w-auto">{action}</div>}
    </div>
  );
}

export function MetricTile({ label, value, accent = false, sub }: { label: string; value: ReactNode; accent?: boolean; sub?: ReactNode }) {
  return (
    <div className="min-w-0 rounded-lg bg-surface-container-low p-space-sm">
      <p className="font-label-meta text-label-meta tracking-wider text-outline uppercase">{label}</p>
      <p className={`font-label-numeric text-headline-md font-bold ${accent ? "text-primary" : "text-on-surface"}`}>
        {value}
        {sub && <span className="ml-1 font-label-meta text-[11px] font-normal text-outline">{sub}</span>}
      </p>
    </div>
  );
}
