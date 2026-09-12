import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Users } from "lucide-react";
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

export const Route = createFileRoute("/games")({
  component: Games,
});

function Games() {
  const [liveGames, setLiveGames] = useState<Game[]>([]);

  useEffect(() => {
    api.listGames().then(setLiveGames).catch(() => {});
  }, []);

  const displayGames = GAMES.map((meta) => {
    const live = liveGames.find((g) => g.slug === meta.id);
    return { ...meta, playersToday: live?.players_today ?? 0 };
  });

  return (
    <main className="min-h-screen pb-24 md:pt-16 md:pb-10">
      <BrandHeader />
      <div className="mx-auto max-w-5xl px-4 md:px-6">
        <h1 className="text-3xl">Games</h1>
        <p className="mt-1 text-sm text-muted-foreground">Pick a lane. Everything's playable without an account.</p>
        <ul className="mt-4 grid gap-3 md:grid-cols-2">
          {displayGames.map((game) => (
            <li key={game.id}>
              <Link to={game.path} className="flex gap-3 rounded-2xl border border-border bg-card p-3">
                <img
                  src={THUMBS[game.id]}
                  alt=""
                  loading="lazy"
                  width={768}
                  height={512}
                  className="h-24 w-24 shrink-0 rounded-xl object-cover"
                />
                <div className="min-w-0 flex-1">
                  <h2 className="truncate text-xl leading-tight">{game.name}</h2>
                  <p className="mt-0.5 text-sm text-muted-foreground">{game.hook}</p>
                  <div className="mt-2 flex flex-wrap gap-x-3 text-xs font-semibold text-muted-foreground">
                    {game.playersToday > 0 && (
                      <span className="inline-flex items-center gap-1">
                        <Users className="h-3.5 w-3.5" />
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
      </div>
      <BottomNav />
    </main>
  );
}
