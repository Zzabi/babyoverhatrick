import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Play, Users } from "lucide-react";
import { BrandHeader } from "@/components/BrandHeader";
import { BottomNav } from "@/components/BottomNav";
import { GAMES } from "@/lib/game-data";
import { api, type Game } from "@/lib/api";
import guessThumb from "@/assets/game-guess.jpg";
import unscrambleThumb from "@/assets/game-unscramble.jpg";

const THUMBS: Record<string, string> = {
  "guess-the-cricketer": guessThumb,
  "unscramble-the-name": unscrambleThumb,
};

export const Route = createFileRoute("/")({
  component: Home,
});

function Home() {
  const [liveGames, setLiveGames] = useState<Game[]>([]);

  useEffect(() => {
    api.listGames().then(setLiveGames).catch(() => {/* fall back to static meta */});
  }, []);

  // Merge static metadata (name, hook, path) with live player counts from API
  const displayGames = GAMES.map((meta) => {
    const live = liveGames.find((g) => g.slug === meta.id);
    return { ...meta, playersToday: live?.players_today ?? 0 };
  });

  const totalToday = displayGames.reduce((sum, g) => sum + g.playersToday, 0);

  return (
    <main className="min-h-screen pb-24 md:pt-16 md:pb-10">
      <BrandHeader />

      {/* Daily Challenge */}
      <section className="px-4 md:px-6">
        <div className="mx-auto max-w-5xl overflow-hidden rounded-2xl border-2 border-foreground/80 scoreboard-panel grain">
          <div className="grid gap-4 p-4 md:grid-cols-[1fr_auto] md:items-center md:p-6">
            <div className="min-w-0">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-accent px-2.5 py-1 text-[11px] font-bold uppercase tracking-widest text-accent-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-foreground" /> Daily challenge
              </span>
              <h1 className="mt-3 font-display text-3xl leading-none text-scoreboard-foreground md:text-5xl">
                Ten cricketers. Sixty seconds.
              </h1>
              <p className="mt-2 font-sans text-sm text-scoreboard-foreground/80">
                {totalToday > 0
                  ? `${totalToday.toLocaleString()} players have already had a go today.`
                  : "Be the first to play today's challenge."}
              </p>
            </div>
            <Link
              to="/play/guess"
              className="flex min-h-[60px] items-center justify-center gap-2 rounded-xl bg-accent px-6 font-display text-2xl tracking-wide text-accent-foreground tile-press active:tile-press-active md:min-w-[220px]"
            >
              <Play className="h-6 w-6 fill-current" aria-hidden="true" /> Play now
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto mt-7 max-w-5xl px-4 md:px-6">
        <h2 className="text-lg tracking-wide">All games</h2>
        <ul className="mt-3 grid gap-3 md:grid-cols-2">
          {displayGames.map((game) => (
            <li key={game.id}>
              <Link
                to={game.path}
                className="flex gap-3 rounded-2xl border border-border bg-card p-3 shadow-sm md:flex-col"
              >
                <img
                  src={THUMBS[game.id]}
                  alt=""
                  loading="lazy"
                  width={768}
                  height={512}
                  className="h-24 w-24 shrink-0 rounded-xl object-cover md:h-36 md:w-full"
                />
                <div className="min-w-0 flex-1">
                  <h3 className="min-w-0 truncate text-xl leading-tight">{game.name}</h3>
                  <p className="mt-0.5 line-clamp-2 text-sm text-muted-foreground">{game.hook}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-semibold text-muted-foreground">
                    {game.playersToday > 0 && (
                      <span className="inline-flex items-center gap-1">
                        <Users className="h-3.5 w-3.5" aria-hidden="true" />
                        <span className="h-1.5 w-1.5 rounded-full bg-live" />
                        {game.playersToday.toLocaleString()} today
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <BottomNav />
    </main>
  );
}
