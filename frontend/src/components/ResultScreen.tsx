import { useState } from "react";
import { Flame, Instagram, RotateCcw, Share2, Shuffle, Check } from "lucide-react";
import { Link } from "@tanstack/react-router";

export type ResultData = {
  gameName: string;
  score: number;
  correct: number;
  total: number;
  streak: number;
  otherGameName: string;
  otherGamePath: string;
  replayPath: string;
};

export function ResultScreen({ data }: { data: ResultData }) {
  const [copied, setCopied] = useState(false);
  const accuracy = data.total > 0 ? Math.round((data.correct / data.total) * 100) : 0;

  function handleCopyLink() {
    const url = window.location.origin + data.replayPath;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    }).catch(() => {
      // Fallback for older browsers
      const ta = document.createElement("textarea");
      ta.value = url;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    });
  }

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-28 md:max-w-2xl md:pb-16">
      <p className="pt-2 text-center text-xs font-bold uppercase tracking-[0.24em] text-muted-foreground">
        {data.gameName} · complete
      </p>

      {/* Shareable result card */}
      <div className="mt-3 overflow-hidden rounded-2xl border-2 border-foreground/80 scoreboard-panel">
        <div className="flex items-center justify-between border-b border-scoreboard-foreground/20 px-4 py-2">
          <span className="font-display text-sm tracking-widest">BABYOVERHATTRICK</span>
          <span className="text-xs opacity-70">#daily</span>
        </div>
        <div className="px-4 py-6 text-center">
          <div className="text-6xl leading-none md:text-7xl">{data.score}</div>
          <div className="mt-2 text-xs uppercase tracking-[0.3em] opacity-70">runs scored</div>
          <div className="mt-5 grid grid-cols-3 gap-2 text-center">
            <Stat label="accuracy" value={`${accuracy}%`} />
            <Stat label="correct" value={`${data.correct}/${data.total}`} />
            <Stat label="streak" value={`${data.streak}`} />
          </div>
        </div>
      </div>

      {data.streak > 0 && (
        <div className="mt-3 flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-3">
          <Flame className="h-5 w-5 shrink-0 text-accent" aria-hidden="true" />
          <p className="min-w-0 text-sm font-semibold">
            {data.streak}-day streak alive. Come back tomorrow to keep it.
          </p>
        </div>
      )}

      <div className="mt-5 grid gap-2.5">
        {/* Play again — forces a full page reload so the session restarts cleanly */}
        <button
          onClick={() => { window.location.href = data.replayPath; }}
          className="flex min-h-[56px] w-full items-center justify-center gap-2 rounded-xl bg-primary font-display text-xl tracking-wide text-primary-foreground tile-press active:tile-press-active"
        >
          <RotateCcw className="h-5 w-5" aria-hidden="true" /> Play again
        </button>

        <Link
          to={data.otherGamePath}
          className="flex min-h-[56px] items-center justify-center gap-2 rounded-xl border border-border bg-secondary font-display text-xl tracking-wide text-secondary-foreground"
        >
          <Shuffle className="h-5 w-5" aria-hidden="true" /> Try {data.otherGameName}
        </Link>

        <div className="grid grid-cols-2 gap-2.5">
          <button
            onClick={handleCopyLink}
            className={`flex min-h-[52px] items-center justify-center gap-2 rounded-xl border text-sm font-bold transition-colors ${
              copied
                ? "border-green-500 bg-green-500/10 text-green-700"
                : "border-border bg-card"
            }`}
          >
            {copied
              ? <><Check className="h-4 w-4" /> Copied! Paste anywhere</>
              : <><Share2 className="h-4 w-4" /> Challenge a friend</>
            }
          </button>
          <a
            href="https://www.instagram.com/babyoverhattrick?stkn=YTNvaThzODZ4OWI5"
            target="_blank"
            rel="noreferrer"
            className="flex min-h-[52px] items-center justify-center gap-2 rounded-xl border border-border bg-card text-sm font-bold"
          >
            <Instagram className="h-4 w-4" aria-hidden="true" /> Follow us
          </a>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-scoreboard-foreground/10 py-2">
      <div className="text-xl leading-none">{value}</div>
      <div className="mt-1 text-[10px] uppercase tracking-widest opacity-70">{label}</div>
    </div>
  );
}

