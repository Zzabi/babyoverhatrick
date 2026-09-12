import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Flame, Trophy } from "lucide-react";
import { BrandHeader } from "@/components/BrandHeader";
import { BottomNav } from "@/components/BottomNav";
import { api, type LeaderboardEntry } from "@/lib/api";

export const Route = createFileRoute("/leaderboard")({
  component: Leaderboard,
});

type Row = { rank: number; name: string; score: number };

function toRows(entries: LeaderboardEntry[]): Row[] {
  return entries.map((e) => ({ rank: e.rank, name: e.username, score: e.score }));
}

function Leaderboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["leaderboard", "guess-the-cricketer", "daily"],
    queryFn: () => api.getLeaderboard("guess-the-cricketer", "daily"),
    retry: 1,
    staleTime: 60_000,
  });

  const rows: Row[] = data && data.entries.length > 0 ? toRows(data.entries) : [];
  const playerCount = data?.entries.length ?? 0;

  return (
    <main className="min-h-screen pb-40 md:pt-16 md:pb-10">
      <BrandHeader />
      <div className="mx-auto max-w-2xl px-4 md:px-6">
        <h1 className="text-3xl">Today's top scores</h1>
        {!isLoading && !isError && (
          <p className="mt-1 text-sm text-muted-foreground">
            Resets at midnight IST.
            {playerCount > 0 ? ` ${playerCount.toLocaleString()} player${playerCount === 1 ? "" : "s"} so far.` : ""}
          </p>
        )}

        {isLoading && (
          <div className="mt-6 flex flex-col gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-14 animate-pulse rounded-xl bg-muted" />
            ))}
          </div>
        )}

        {isError && (
          <div className="mt-6 rounded-2xl border border-border bg-card px-4 py-8 text-center text-muted-foreground">
            Could not load scores right now. Try again shortly.
          </div>
        )}

        {!isLoading && !isError && rows.length === 0 && (
          <div className="mt-6 flex flex-col items-center gap-3 rounded-2xl border border-border bg-card px-4 py-12 text-center">
            <Trophy className="h-10 w-10 text-muted-foreground/50" />
            <p className="font-semibold">No scores yet today</p>
            <p className="text-sm text-muted-foreground">Be the first to play and claim the top spot.</p>
          </div>
        )}

        {rows.length > 0 && (
          <ol className="mt-4 overflow-hidden rounded-2xl border border-border bg-card">
            {rows.map((row) => (
              <li
                key={row.rank}
                className="grid grid-cols-[2.25rem_minmax(0,1fr)_auto] items-center gap-3 border-b border-border px-3 py-3 last:border-b-0"
              >
                <span className="font-display text-xl leading-none text-muted-foreground">
                  {row.rank <= 3 ? ["🥇", "🥈", "🥉"][row.rank - 1] : row.rank}
                </span>
                <span className="min-w-0">
                  <span className="block truncate font-semibold">{row.name}</span>
                </span>
                <span className="shrink-0 rounded-md bg-scoreboard px-2.5 py-1 font-score text-lg leading-none text-scoreboard-foreground tabular-nums">
                  {row.score}
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>

      <BottomNav />
    </main>
  );
}
