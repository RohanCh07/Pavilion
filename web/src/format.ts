import type { Position, Role } from "./api";

export const ROLE_SHORT: Record<Position, string> = {
  batter: "BAT",
  wicket_keeper: "WK",
  all_rounder: "AR",
  bowler: "BOWL",
};

export const FORMAT_LABEL: Record<string, string> = { t20: "T20", odi: "ODI", test: "Test" };

export const POSITION_ORDER: Position[] = ["wicket_keeper", "batter", "all_rounder", "bowler"];

export const ROLE_TAG: Record<Role, string> = { captain: "C", vice_captain: "VC", player: "" };

export function pts(value: number): string {
  return Number.isInteger(value) ? value.toLocaleString("en-IN") : value.toFixed(1);
}

const dayFmt = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short" });
const timeFmt = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" });
const fullFmt = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

export function shortDate(iso: string): string {
  return dayFmt.format(new Date(iso));
}

export function dateRange(start: string | null, end: string | null): string {
  if (!start) return "";
  const a = dayFmt.format(new Date(start));
  return end ? `${a} – ${dayFmt.format(new Date(end))}` : a;
}

export function startTime(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const sameDay = d.toDateString() === today.toDateString();
  return sameDay ? `Today · ${timeFmt.format(d)}` : fullFmt.format(d);
}

export function startsIn(iso: string): string {
  const mins = Math.round((new Date(iso).getTime() - Date.now()) / 60_000);
  if (mins <= 0) return "Starting soon";
  if (mins < 60) return `Starts in ${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 48) return `Starts in ${hours}h ${mins % 60}m`;
  return `Starts in ${Math.floor(hours / 24)} days`;
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0] ?? "")
    .join("")
    .toUpperCase();
}

export function shortName(name: string): string {
  const words = name.trim().split(/\s+/);
  return words.length > 1 ? `${words[0][0]}. ${words.slice(1).join(" ")}` : name;
}
