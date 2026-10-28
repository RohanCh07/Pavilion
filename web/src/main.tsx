import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import { Icon } from "./components/Icon";
import { Layout, type NavKey } from "./components/Layout";
import { btnPrimary, EmptyPanel } from "./components/ui";
import { navigate, useData, useRoute } from "./hooks";
import "./index.css";
import { Builder } from "./pages/Builder";
import { Home } from "./pages/Home";
import { Leaderboards } from "./pages/Leaderboards";
import { Matches } from "./pages/Matches";
import { MyTeams } from "./pages/MyTeams";
import { PoolCreate, PoolPage, Pools } from "./pages/Pools";
import { Rules } from "./pages/Rules";
import { ScorecardPage } from "./pages/ScorecardPage";
import { SeriesPage } from "./pages/SeriesPage";
import { TeamPage } from "./pages/TeamPage";
import { UserGate, useUser } from "./user";

/*
 Routes (hash based):
   #/                              series list
   #/series/:id[?tab=teams|leaderboard]
   #/series/:id/build[?match=:mid] create a series or match team
   #/series/:id/match/:mid         scorecard with points
   #/matches                       match center
   #/teams                         my teams
   #/teams/:id                     team score
   #/teams/:id/edit                edit a team
   #/pools                         my pools
   #/pools/new[?series=&match=]    create a pool
   #/pools/:id                     pool with its leaderboard
   #/pools/:id/add                 add a team to a pool
   #/leaderboards                  rankings
   #/rules                         rules & scoring
*/
function App() {
  const { path, query } = useRoute();
  const user = useUser();
  const myTeams = useData(() => api.myTeams(), [user, path.join("/")]);
  const [a, b, c, d] = path;
  const id = Number(b);
  const where = path.join("/");
  useEffect(() => window.scrollTo(0, 0), [where]); // each screen opens at the top

  let nav: NavKey | null = null;
  let page;
  if (!a) {
    nav = "series";
    page = <Home />;
  } else if (a === "series" && id && c === "build") {
    nav = "teams";
    page = <Builder key={`new-${id}-${query.get("match")}`} seriesId={id} matchId={Number(query.get("match")) || null} />;
  } else if (a === "series" && id && c === "match" && Number(d)) {
    nav = "matches";
    page = <ScorecardPage key={`${id}-${d}`} seriesId={id} matchId={Number(d)} />;
  } else if (a === "series" && id) {
    nav = "series";
    const tab = query.get("tab");
    page = <SeriesPage key={id} seriesId={id} tab={tab === "teams" || tab === "leaderboard" ? tab : "matches"} />;
  } else if (a === "teams" && id && c === "edit") {
    nav = "teams";
    page = <Builder key={`edit-${id}`} seriesId={0} matchId={null} teamId={id} />;
  } else if (a === "teams" && id) {
    nav = "teams";
    page = <TeamPage key={id} teamId={id} />;
  } else if (a === "teams") {
    nav = "teams";
    page = <MyTeams />;
  } else if (a === "pools" && b === "new") {
    nav = "pools";
    page = (
      <PoolCreate key={`${query.get("series")}-${query.get("match")}`} seriesId={Number(query.get("series")) || null} matchId={Number(query.get("match")) || null} />
    );
  } else if (a === "pools" && id && c === "add") {
    nav = "pools";
    page = <Builder key={`pool-add-${id}`} seriesId={0} matchId={null} poolId={id} />;
  } else if (a === "pools" && id) {
    nav = "pools";
    page = <PoolPage key={id} poolId={id} />;
  } else if (a === "pools") {
    nav = "pools";
    page = <Pools />;
  } else if (a === "matches") {
    nav = "matches";
    page = <Matches />;
  } else if (a === "leaderboards") {
    nav = "leaderboard";
    page = <Leaderboards />;
  } else if (a === "rules") {
    nav = "rules";
    page = <Rules />;
  } else {
    page = (
      <EmptyPanel
        icon="explore_off"
        title="Page not found"
        action={
          <button type="button" className={`${btnPrimary} px-space-xl py-space-sm`} onClick={() => navigate("/")}>
            <Icon name="home" className="text-[18px]" /> Go to Series
          </button>
        }
      />
    );
  }

  return (
    <Layout active={nav} teamCount={myTeams.data?.length}>
      {page}
    </Layout>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <UserGate>
      <App />
    </UserGate>
  </StrictMode>,
);
