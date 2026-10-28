---
name: Pavilion Fantasy Cricket
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3c4a42'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6c7a71'
  outline-variant: '#bbcabf'
  surface-tint: '#006c49'
  primary: '#006c49'
  on-primary: '#ffffff'
  primary-container: '#10b981'
  on-primary-container: '#00422b'
  inverse-primary: '#4edea3'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#855300'
  on-tertiary: '#ffffff'
  tertiary-container: '#e29100'
  on-tertiary-container: '#523200'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#6ffbbe'
  primary-fixed-dim: '#4edea3'
  on-primary-fixed: '#002113'
  on-primary-fixed-variant: '#005236'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  headline-xl:
    fontFamily: Geist
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.025em
  headline-xl-mobile:
    fontFamily: Geist
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Geist
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.015em
  body-lg:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-numeric:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: -0.01em
  label-badge:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 12px
    letterSpacing: 0.04em
  label-meta:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-tablet: 1.5rem
  margin-desktop: 2.5rem
  space-2xs: 0.125rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
  space-2xl: 2rem
---

## Brand & Style

This design system is tailored for a high-performance fantasy cricket platform built around speed, precision, and statistical clarity. The aesthetic merges clean sports telemetry with contemporary product minimalism—dispensing with loud gradients, chaotic advertising banners, and skeuomorphic stadium tropes in favor of razor-sharp hierarchy, generous negative space, and disciplined data density.

### Aesthetic Foundation
- **Modern Minimalist High-Utility:** Crisp surface-on-surface separation, purposeful borders, and meticulous typographic contrast.
- **Electric Precision:** High-vibe pitch green accenting applied surgically against cool slate neutrals to denote live action, tactical gains, and primary user momentum.
- **Data-Dense Yet Breathable:** Live cricket demands fast ingestion of overs, run rates, boundary counts, player fantasy credits, and multipliers ($C$ and $VC$). Visual fatigue is minimized through systematic spacing and tabular typography.

## Colors

The palette employs a restrained grayscale hierarchy dominated by light zinc/slate backdrops, permitting the emerald pitch green to deliver immediate functional intent.

### Palette Roles
- **Primary Turf Green (`#10B981` / Emerald 500):** Reserved exclusively for active live indicators, positive score deltas, selected captain roles, locked team confirmations, and primary CTAs.
- **Deep Slate Ground (`#0F172A` / Slate 900):** Anchors high-emphasis headings, key player metric titles, and strong inverted tooltips.
- **Accent Warning/Boundary (`#F59E0B` / Amber 500):** Denotes match critical events (e.g., DRS reviews, rain delay alerts, pending toss notices).
- **Neutral Canvas (`#F8FAFC` to `#FFFFFF` in Light; `#0B0F17` to `#1E293B` in Dark):** Pure neutral slate backing with clean structural delineation.

### Dark Mode Adaptations
- Background Canvas: `#090D16`
- Elevated Card Surfaces: `#111827`
- Inactive Borders: `#1E293B`
- Active / Live Glow: `#10B981` at 15% opacity halo over `#10B981` foreground.

## Typography

The type scale leverages **Geist** for crisp readability across mobile scoreboards and team rosters, coupled with **JetBrains Mono** for all numerical scores, strike rates, overs calculations, and point tallies.

### Typographic Principles
- **Tabular Alignment:** All cricket runs, fantasy credits, rank positions, and economy rates must strictly enforce `font-variant-numeric: tabular-nums` to eliminate jitter during live real-time score updates.
- **Visual Weighting:** Metric labels use uppercase tracking (`0.04em`), small font size (`11px`), and subdued slate shades (`#64748B`), allowing big numerical scores (`label-numeric` or `headline-md`) to lead the visual hierarchy.

## Layout & Spacing

A mobile-first fluid layout architecture scaled for handheld speed and extended to a structured multi-column desktop layout.

### Breakpoints & Layout Adaptations
- **Mobile (< 768px):** Single-column layout. Content runs edge-to-edge within `margin: 1rem`. A fixed floating bottom navigation bar (`height: 64px`) houses core match routes (Matches, My Contests, Leaderboard, Wallet).
- **Tablet (768px - 1023px):** 8-column layout. Match listings and contest lobbies transition into 2-column cards.
- **Desktop (≥ 1024px):** Fixed-width persistent sidebar (`260px`) on the left, an 8-column main match feed / fantasy builder center column, and a 4-column contextual panel on the right (displaying live point delta feeds, active captain boosters, or mini pitch infographics).

### Spacing Engine
A standard 4px/8px incremental base rhythm. Vertical rhythm inside player listing rows strictly utilizes `space-sm` (8px) and `space-md` (12px) to optimize vertical scroll velocity while preserving touch targets (`min-height: 48px`).

## Elevation & Depth

Visual hierarchy relies on low-contrast structural outlines paired with micro-diffused ambient elevations. This system rejects heavy, muddy dropshadows in favor of razor-clean boundary delineation.

### Elevation Hierarchy
- **Level 0 (Canvas Base):** Flat `#F8FAFC` (`#090D16` dark). No border, no shadow.
- **Level 1 (Card & Row Surfaces):** Pure `#FFFFFF` (`#111827` dark) backed by a crisp 1px solid stroke of `#E2E8F0` (`#1E293B` dark) and a low-opacity ambient drop: `0px 1px 3px rgba(15, 23, 42, 0.04), 0px 4px 10px rgba(15, 23, 42, 0.02)`.
- **Level 2 (Active Selector & Modals):** Team builder active player rows, dropdown sheets, and sticky header bars. Boundary stroke `#CBD5E1` with `0px 8px 24px -4px rgba(15, 23, 42, 0.08)`.
- **Level 3 (Floating HUD & Bottom Nav):** Floating mobile navigation and contest confirmation drawers. Backdrop filter `blur(12px)` over 85% opacity surface fills (`rgba(255, 255, 255, 0.85)` / `rgba(17, 24, 39, 0.85)`) with a top border stroke of `#E2E8F0` / `#1E293B`.

## Shapes

The design system maintains a refined balance between structured data containers and organic, ergonomic touch components.

### Rounding Matrix
- **Cards & Data Modules (`rounded-lg` / 16px):** Outer match cards, contest cards, leaderboard containers, and scorecard summaries.
- **Interactive Controls (`rounded` / 8px):** Input fields, square tab selectors, and filter buttons.
- **System Tags & Micro Badges (Full Pill / 9999px):** Match statuses (Upcoming, Live, Finished), player role indicators, credit tokens, and multiplier toggles.

## Components

### Buttons
- **Primary Action (Confirm XI, Join Contest):** Background `#10B981`, text `#FFFFFF`, font-weight 600, border radius `8px`. Hover: `#059669`. Active scale down `0.98` with immediate transition (`100ms ease-out`).
- **Secondary (Share XI, Rules):** Background transparent, 1px solid `#E2E8F0`, text `#0F172A`. Hover: `#F1F5F9`.
- **Ghost Action:** Background transparent, text `#64748B`, hover text `#0F172A`.

### Status Chips & Badges
- **Live Status:** Pill shape, background `#ECFDF5` (`#064E3B` dark), text `#059669` (`#34D399` dark). Prepended with a 6px circular dot pulsating via CSS keyframe (`1.5s infinite`).
- **Upcoming Status:** Background `#F1F5F9`, text `#475569`.
- **Finished Status:** Background `#F8FAFC`, text `#94A3B8`, border 1px solid `#E2E8F0`.
- **Role Badges (`BAT`, `BOWL`, `WK`, `AR`):** 20px height, uppercase `label-badge`, padding `2px 6px`, border-radius `4px`. Background `#F1F5F9` (`#1E293B` dark), text `#475569` (`#94A3B8` dark).
- **Multiplier Circles ($C$ and $VC$):** 28px × 28px circular badges. Inactive: 1px solid `#CBD5E1`, text `#64748B`. Active Selected: background `#10B981` (for Captain 2x) or `#0F172A` (for Vice-Captain 1.5x) with sharp white centered glyph.

### Cards & Player Selector Rows
- **Match Card:** Rounded 16px, background `#FFFFFF`, border 1px solid `#E2E8F0`. Features two team rows with flag circles, team abbreviations in `headline-md`, live match timer/score right-aligned in `label-numeric`, and bottom contest prize pool bar.
- **Roster Selection Row:** Horizontal layout, height 56px, dividing hairline `#F1F5F9`. Left: player avatar with role tag overlay. Center: player name, country code, selected percentage. Right: fantasy credits (`JetBrains Mono`) and an emerald plus/check toggle button.

### Form Inputs & Filters
- **Search & Credit Filter:** Background `#FFFFFF`, 1px solid `#CBD5E1`, padding `10px 14px`, border-radius `8px`. Focus state shifts border color immediately to `#10B981` with an outer focus ring: `0 0 0 3px rgba(16, 185, 129, 0.15)`.

### Feedback & Loading Patterns
- **Skeleton Shimmer:** High-velocity linear shimmer across placeholder player names and scores (`#E2E8F0` to `#F1F5F9`). Avoids spinner wheels to sustain perceived speed during live data refreshes.