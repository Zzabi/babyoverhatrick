import { useEffect, useRef, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Lightbulb, X, ChevronRight, Layers } from "lucide-react";
import { BottomNav } from "@/components/BottomNav";
import { SignInSheet } from "@/components/SignInSheet";
import { ResultScreen } from "@/components/ResultScreen";
import { api, type SessionQuestion, type AnswerResult, type GameSet } from "@/lib/api";
import { GAME_CONFIG } from "@/lib/config";

export const Route = createFileRoute("/play/unscramble")({
  component: UnscrambleGame,
});

const GAME_SLUG = "unscramble-the-name";
const ROUND_SECONDS = GAME_CONFIG.UNSCRAMBLE_ROUND_SECONDS;

/** Show the sign-in prompt at most once per browser session. */
function tryPromptSignIn(set: (v: boolean) => void) {
  if (!sessionStorage.getItem("sign_in_prompted")) {
    sessionStorage.setItem("sign_in_prompted", "1");
    set(true);
  }
}

/** Split the flat scrambled_letters array on the " " separator into word groups. */
function toWordGroups(letters: string[]): string[][] {
  const groups: string[][] = [];
  let current: string[] = [];
  for (const ch of letters) {
    if (ch === " ") {
      if (current.length) groups.push(current);
      current = [];
    } else {
      current.push(ch);
    }
  }
  if (current.length) groups.push(current);
  return groups.length ? groups : [letters];
}

/**
 * Hint tiers for Unscramble:
 *  hintPhase 0 → nothing revealed (country/role hidden)
 *  hintPhase 1 → country revealed
 *  hintPhase 2 → role revealed
 *  hintPhase 3+ → server DB hints (accepted_aliases)
 */
function UnscrambleGame() {
  const [phase, setPhase] = useState<"setup" | "loading" | "error" | "playing" | "done">("setup");
  const [sets, setSets] = useState<GameSet[]>([]);
  const [selectedSetId, setSelectedSetId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [questions, setQuestions] = useState<SessionQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [correct, setCorrect] = useState(0);
  const [seconds, setSeconds] = useState<number>(ROUND_SECONDS);
  const [typed, setTyped] = useState("");
  /** 0=nothing, 1=country shown, 2=role shown, 3+=server hints */
  const [hintPhase, setHintPhase] = useState(0);
  const [serverHints, setServerHints] = useState<string[]>([]);
  const [lastResult, setLastResult] = useState<AnswerResult | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [promptSignIn, setPromptSignIn] = useState(false);
  const [finalResult, setFinalResult] = useState<{ score: number; correct: number; total: number } | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const inputRef = useRef<HTMLInputElement>(null);

  const TOTAL = questions.length;
  const currentQ = questions[index];
  const wordGroups = toWordGroups(currentQ?.scrambled_letters ?? []);

  // DB hints start at index 1 (index 0 is the canonical answer stored in aliases)
  const dbHintCount = Math.max(0, (currentQ?.hint_count ?? 0) - 1);
  // Total available hint presses: country + role + DB hints
  const totalHints = 2 + dbHintCount;
  const hintsUsed = hintPhase; // each press = 1 hint used

  // ── Fetch sets ─────────────────────────────────────────────────────────────
  useEffect(() => {
    api.listGameSets(GAME_SLUG).then(setSets).catch(() => {});
  }, []);

  // ── Start session ───────────────────────────────────────────────────────────
  function startGame(setId: number | null) {
    setPhase("loading");
    const guestToken = localStorage.getItem("boh_guest_token") ?? (() => {
      const t = crypto.randomUUID();
      localStorage.setItem("boh_guest_token", t);
      return t;
    })();

    const playedKey = `played_qids_${GAME_SLUG}`;
    const played: number[] = JSON.parse(sessionStorage.getItem(playedKey) ?? "[]");

    api.startSession({
      game_slug: GAME_SLUG,
      ...(setId !== null ? { set_id: setId } : {}),
      guest_token: guestToken,
      exclude_ids: played,
    })
      .then((res) => {
        setSessionId(res.session_id);
        setQuestions(res.questions);
        if (res.questions.length === 0) {
          setError("No questions yet — check back soon!");
          setPhase("error");
        } else {
          setPhase("playing");
          startTimeRef.current = Date.now();
        }
      })
      .catch((e) => { setError(e.message); setPhase("error"); });
  }

  // ── Timer ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== "playing" || showResult) return;
    if (seconds <= 0) { submitAnswer("", true); return; }
    const t = setTimeout(() => setSeconds((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [seconds, phase, showResult]);

  // ── Helpers ────────────────────────────────────────────────────────────────
  async function submitAnswer(answer: string, timedOut = false) {
    if (!sessionId || !currentQ || showResult) return;
    const elapsed = Math.round(Date.now() - startTimeRef.current);

    try {
      const result = await api.submitAnswer(sessionId, {
        question_id: currentQ.id,
        ...(timedOut ? {} : { answer_given: answer }),
        response_time_ms: elapsed,
        hints_used: hintsUsed,
      });
      setLastResult(result);
      if (result.is_correct) {
        setScore((s) => s + result.points_earned);
        setCorrect((c) => c + 1);
      }
      setShowResult(true);
    } catch {
      advanceQuestion(null);
    }
  }

  function advanceQuestion(_result: AnswerResult | null) {
    setShowResult(false);
    setLastResult(null);
    setTyped("");
    setHintPhase(0);
    setServerHints([]);
    startTimeRef.current = Date.now();

    const next = index + 1;
    if (next >= TOTAL) {
      // Persist played question IDs to avoid repeats next game
      const playedKey = `played_qids_${GAME_SLUG}`;
      const prev: number[] = JSON.parse(sessionStorage.getItem(playedKey) ?? "[]");
      const merged = Array.from(new Set([...prev, ...questions.map((q) => q.id)]));
      sessionStorage.setItem(playedKey, JSON.stringify(merged));

      if (sessionId) {
        api.completeSession(sessionId).then((res) => {
          setFinalResult({ score: res.score, correct: res.correct, total: res.total });
          setPhase("done");
          tryPromptSignIn(setPromptSignIn);
        }).catch(() => {
          setFinalResult({ score, correct, total: TOTAL });
          setPhase("done");
        });
      } else {
        setPhase("done");
      }
      return;
    }
    setIndex(next);
    setSeconds(ROUND_SECONDS);
  }

  async function handleHint() {
    if (!sessionId || !currentQ || hintsUsed >= totalHints) return;

    if (hintPhase === 0) {
      // Hint 1: reveal country
      setHintPhase(1);
    } else if (hintPhase === 1) {
      // Hint 2: reveal role
      setHintPhase(2);
    } else {
      // Hint 3+: fetch from server DB
      const serverHintIndex = hintPhase - 2; // maps to DB hint index 0, 1, 2...
      try {
        const result = await api.getHint(sessionId, currentQ.id, serverHintIndex);
        if (result.hint) {
          setServerHints((h) => [...h, result.hint!]);
          setHintPhase((p) => p + 1);
        }
      } catch { /* exhausted */ }
    }
  }

  // ── Render: Setup ─────────────────────────────────────────────────────────
  if (phase === "setup") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
        <div className="w-full max-w-sm">
          <p className="text-center text-xs font-bold uppercase tracking-[0.24em] text-muted-foreground mb-2">
            Unscramble the Name
          </p>
          <div className="rounded-2xl border border-border bg-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Layers className="h-5 w-5 text-muted-foreground" />
              <h2 className="font-display text-2xl">Choose a set</h2>
            </div>

            <div className="grid gap-2">
              <button
                onClick={() => setSelectedSetId(null)}
                className={`rounded-xl border-2 px-4 py-3 text-left text-sm font-bold transition-colors ${
                  selectedSetId === null
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border bg-background text-muted-foreground"
                }`}
              >
                🎲 All sets
              </button>

              {sets
                .filter((s) => !/^default(\s+set)?$/i.test(s.name.trim()))
                .map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setSelectedSetId(s.id)}
                    className={`rounded-xl border-2 px-4 py-3 text-left text-sm font-bold transition-colors ${
                      selectedSetId === s.id
                        ? "border-primary bg-primary/10 text-foreground"
                        : "border-border bg-background text-muted-foreground"
                    }`}
                  >
                    {s.name}
                    <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      {s.difficulty}
                    </span>
                  </button>
                ))}
            </div>

            <button
              onClick={() => startGame(selectedSetId)}
              className="mt-5 flex w-full min-h-[52px] items-center justify-center gap-2 rounded-xl bg-primary font-display text-2xl tracking-wide text-primary-foreground tile-press active:tile-press-active"
            >
              Start Game
            </button>

            <Link to="/" className="mt-3 block text-center text-xs text-muted-foreground hover:text-foreground">
              ← Back to games
            </Link>
          </div>
        </div>
        <BottomNav />
      </main>
    );
  }

  if (phase === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="mt-3 text-sm text-muted-foreground">Loading game…</p>
        </div>
      </main>
    );
  }

  if (phase === "error") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="max-w-sm text-center">
          <p className="text-2xl">🏏</p>
          <h2 className="mt-3 font-display text-2xl">{error}</h2>
          <Link to="/" className="mt-4 inline-block text-sm font-semibold underline">Back to games</Link>
        </div>
      </main>
    );
  }

  if (phase === "done" && finalResult) {
    return (
      <main className="min-h-screen pt-4 md:pt-20">
        <ResultScreen
          data={{
            gameName: "Unscramble the Name",
            score: finalResult.score,
            correct: finalResult.correct,
            total: finalResult.total,
            streak: 0,
            otherGameName: "Guess the Cricketer",
            otherGamePath: "/play/guess",
            replayPath: "/play/unscramble",
          }}
        />
        <SignInSheet open={promptSignIn} onDismiss={() => setPromptSignIn(false)} />
        <BottomNav />
      </main>
    );
  }

  if (!currentQ) return null;

  const hintsRemaining = Math.max(0, totalHints - hintsUsed);

  return (
    <main className="min-h-screen pb-28 md:pt-20 md:pb-10">
      <div className="mx-auto w-full max-w-md px-4 md:max-w-2xl md:px-6">

        {/* HUD */}
        <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 pt-4">
          <Link to="/" aria-label="Quit" className="grid h-11 w-11 place-items-center rounded-full bg-secondary text-secondary-foreground">
            <X className="h-5 w-5" />
          </Link>
          <div className="text-center text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
            {index + 1}/{TOTAL}
          </div>
          <div className="rounded-lg px-2.5 py-1.5 scoreboard-panel">
            <span className="font-score text-xl leading-none">{score}</span>
          </div>
        </div>

        {/* Timer */}
        <div className="mt-4 h-3 overflow-hidden rounded-full bg-muted">
          <div
            className={`h-full rounded-full transition-[width] duration-1000 ease-linear ${seconds <= 8 ? "bg-destructive" : "bg-accent"}`}
            style={{ width: `${(seconds / ROUND_SECONDS) * 100}%` }}
          />
        </div>

        {/* Clue card — country/role revealed progressively via hints */}
        <div className="mt-4 flex items-center gap-4 rounded-2xl border border-border bg-pitch px-5 py-4 grain">
          <span className={`grid h-14 w-14 shrink-0 place-items-center rounded-full font-display text-lg tracking-wider transition-colors ${
            hintPhase >= 1 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
          }`}>
            {hintPhase >= 1 ? (currentQ.country ?? "?") : "?"}
          </span>
          <span className="min-w-0">
            <span className="block font-display text-2xl leading-tight">
              {hintPhase >= 1 ? (currentQ.country ?? "?") : "Use a hint"}
            </span>
            <span className="block text-sm text-muted-foreground">
              {hintPhase >= 2 ? (currentQ.role ?? "") : hintPhase === 1 ? "Role — hint 2" : "Country & Role hidden"}
            </span>
          </span>
        </div>

        {/* Scrambled tiles — visual hint, grouped by word */}
        {!showResult && (
          <div className="mt-5">
            <p className="mb-2 text-xs font-bold uppercase tracking-widest text-muted-foreground text-center">
              Scrambled letters
            </p>
            <div className="flex flex-wrap justify-center gap-x-5 gap-y-2">
              {wordGroups.map((group, gi) => (
                <div key={gi} className="flex flex-wrap justify-center gap-1.5">
                  {group.map((letter, li) => (
                    <span
                      key={li}
                      className="grid h-11 w-9 place-items-center rounded-lg bg-secondary font-score text-xl text-secondary-foreground select-none"
                    >
                      {letter}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Result feedback */}
        {showResult && lastResult && (
          <div className={`mt-4 rounded-xl border-2 p-4 ${lastResult.is_correct ? "border-green-500 bg-green-500/10" : "border-destructive bg-destructive/10"}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-display text-xl">
                  {lastResult.is_correct ? "✅ Correct!" : "❌ Not quite"}
                </p>
                {!lastResult.is_correct && lastResult.correct_answer && (
                  <p className="mt-1 text-sm text-muted-foreground">
                    Answer: <strong>{lastResult.correct_answer}</strong>
                  </p>
                )}
              </div>
              {lastResult.is_correct && (
                <span className="rounded-lg bg-green-500/20 px-2 py-1 font-score text-lg text-green-700">
                  +{lastResult.points_earned}
                </span>
              )}
            </div>
            <button
              onClick={() => advanceQuestion(lastResult)}
              className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-xl bg-primary py-3 font-display text-lg tracking-wide text-primary-foreground tile-press"
            >
              {index + 1 < TOTAL ? "Next" : "See Results"} <ChevronRight className="h-5 w-5" />
            </button>
          </div>
        )}

        {/* Server DB hints */}
        {serverHints.length > 0 && (
          <ul className="mt-3 grid gap-1.5">
            {serverHints.map((h, i) => (
              <li key={i} className="rounded-lg bg-secondary px-3 py-2 text-sm font-semibold text-secondary-foreground">
                💡 {h}
              </li>
            ))}
          </ul>
        )}

        {/* Text input — primary interaction */}
        {!showResult && (
          <>
            <div className="mt-4">
              <input
                ref={inputRef}
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && typed.trim()) submitAnswer(typed.trim());
                }}
                placeholder={
                  wordGroups.length > 1
                    ? "Type first and last name…"
                    : "Type the cricketer's name…"
                }
                autoComplete="off"
                spellCheck={false}
                autoCapitalize="words"
                className="w-full min-h-[60px] rounded-xl border border-input bg-card px-4 text-lg uppercase tracking-widest outline-none focus:border-ring focus:ring-2 focus:ring-ring/30 placeholder:normal-case placeholder:tracking-normal"
              />
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2.5">
              <button
                disabled={!typed.trim()}
                onClick={() => submitAnswer(typed.trim())}
                className="min-h-[52px] rounded-xl bg-primary px-4 font-display text-lg tracking-wide text-primary-foreground tile-press disabled:opacity-40"
              >
                Submit
              </button>
              <button
                disabled={hintsRemaining === 0}
                onClick={handleHint}
                className="flex min-h-[52px] items-center justify-center gap-2 rounded-xl border border-dashed border-border text-sm font-bold text-muted-foreground disabled:opacity-40"
              >
                <Lightbulb className="h-4 w-4" />
                {hintPhase === 0 ? "Country" : hintPhase === 1 ? "Role" : "Hint"} ({hintsRemaining} left)
              </button>
            </div>
          </>
        )}
      </div>
      <BottomNav />
    </main>
  );
}
