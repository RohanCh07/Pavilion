import { requestRefresh, useCooldown } from "../refresh";
import { Icon } from "./Icon";

/** Reloads the screen's data on tap; then waits a minute before it can be used again. */
export function RefreshButton() {
  const left = useCooldown();
  const cooling = left > 0;
  const label = cooling ? `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}` : "Refresh";
  return (
    <button
      type="button"
      onClick={() => requestRefresh()}
      disabled={cooling}
      aria-label={cooling ? `Refresh available in ${left} seconds` : "Refresh scores"}
      title={cooling ? "You can refresh once a minute" : "Get the latest scores and points"}
      className={`inline-flex items-center gap-space-2xs rounded-lg px-space-sm py-space-xs font-body-sm text-body-sm font-semibold transition-colors ${
        cooling
          ? "cursor-not-allowed bg-surface-container-low font-label-numeric text-outline"
          : "bg-surface-container text-primary hover:bg-surface-container-high"
      }`}
    >
      <Icon name={cooling ? "timer" : "refresh"} className="text-[18px]" />
      <span>{label}</span>
    </button>
  );
}
