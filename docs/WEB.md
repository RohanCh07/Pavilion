# Web app (Pavilion)

The phone-first front end in `web/`, built to match the Stitch "Pavilion" design in
`web/design/` (screenshots, exported HTML and `DESIGN.md`). It talks only to the web API
([API.md](API.md)), and the API serves the built app, so one command runs both.

The design's colour tokens, type scale and spacing names are ported 1:1 into
`src/index.css`, so classes like `bg-surface-container-low`, `text-headline-md` or
`p-space-lg` mean exactly what they mean in the Stitch export, and its markup can be reused
as is. Icons are Material Symbols, as in the design; `index.html` loads only the glyphs the
app uses (add a name there when you use a new icon).

## Run it

```powershell
# once: build the app (needs Node 20+)
cd web
npm install
npm run build
cd ..

# then start the API, which serves the app at /
$env:DATA_PROVIDER = "crex"
python -m fantasy_bot.api
```

Open <http://127.0.0.1:8000>.

**On your phone:** set `API_HOST=0.0.0.0` in `.env`, start the API, and open
`http://<your PC's Wi-Fi IP>:8000` on the phone (same Wi-Fi). Windows may ask to allow
Python through the firewall the first time. In the phone's browser menu, "Add to Home
screen" makes it open like an app.

## Develop

```powershell
python -m fantasy_bot.api   # terminal 1: API on :8000
cd web; npm run dev         # terminal 2: app on :5173 with hot reload, /api proxied to :8000
```

`npm run dev` listens on the network too, so the phone can open `http://<PC IP>:5173`.
`npm run typecheck` checks types.

## Screens

| Route | Screen |
|---|---|
| `#/` | Series list (design: home_series_list) |
| `#/series/:id` | Series page with matches, my teams and leaderboard (design: series_page_matches) |
| `#/series/:id/build[?match=:mid]` | Team builder for the series, or one match (design: team_builder_create_edit) |
| `#/series/:id/match/:mid` | Scorecard with each player's raw stats and points |
| `#/teams` | My teams (design: my_teams_management) |
| `#/matches` | Match center: live, upcoming and recent matches across series |
| `#/rules` | Rules & scoring |
| `#/teams/:id` | Team score: total, per player, per match with point breakdowns |
| `#/teams/:id/edit` | Edit a team (locked once its match starts) |
| `#/leaderboards` | Rankings: top 5 of every series you have a series team in |
| `#/pools` | My pools |
| `#/pools/new[?series=&match=]` | Create a pool: name, type (normal / Dream Team), series or match, teams |
| `#/pools/:id` | A pool and its leaderboard |
| `#/pools/:id/add` | Add a team to a pool |

## How it's built for phones

- Mobile first: single column, bottom navigation, 44px+ tap targets, a sticky save bar in the
  team builder, safe-area padding for the iPhone home bar, 16px inputs so iOS doesn't zoom.
  At 1024px and up it switches to the design's sidebar layout.
- Small and fast: written against React's API but bundled with Preact (about 35 KB of
  JavaScript and 10 KB of CSS gzipped), with a subset icon font. Match cards only fetch
  their top performers once scrolled into view.
- Feels instant: API reads are cached in memory for 30 seconds and loading shows skeletons.
- Nothing refreshes on its own. The Refresh button in the top bar reloads everything on the
  current screen with fresh data, then counts down a 1-minute cooldown (kept across reloads)
  before it can be used again (`src/refresh.ts`).
- Light theme, as in the design.

Where the design shows data the backend doesn't have yet (credits, prize pool, selected %,
form, venue conditions), the slot is kept and shows "—" or "coming soon", so the layout
matches the mockups and fills in when that data exists.

## Users

There's no login yet. On first visit the app asks for a name and sends it as `X-User-Id`, so
anyone using the same name sees the same teams. Replace this with real login before sharing
the app publicly.

## Layout

```
web/
├── design/               the Stitch export this app is built from
├── index.html            fonts, icon subset, mount point
├── vite.config.ts        Preact aliases, Tailwind, /api proxy for dev
└── src/
    ├── main.tsx          routes
    ├── api.ts            typed API client and cache
    ├── hooks.ts          hash router, data loading with polling, in-view loading
    ├── data.ts           shared loaders (my teams + scores, leaderboard ranks)
    ├── user.tsx          name prompt (X-User-Id)
    ├── format.ts         dates, points, role labels
    ├── index.css         the design's tokens (colours, type scale, spacing)
    ├── components/       layout, match and team cards, small UI parts, icons
    └── pages/            one file per screen
```
