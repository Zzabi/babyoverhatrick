import { useCallback, useEffect, useRef, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Lightbulb, X, ChevronRight, Layers } from "lucide-react";
import { BottomNav } from "@/components/BottomNav";
import { SignInSheet } from "@/components/SignInSheet";
import { ResultScreen } from "@/components/ResultScreen";
import { api, type SessionQuestion, type AnswerResult, type GameSet } from "@/lib/api";
import { GAME_CONFIG } from "@/lib/config";

export const Route = createFileRoute("/play/guess")({
  component: GuessGame,
});

const GAME_SLUG = "guess-the-cricketer";
const ROUND_SECONDS = GAME_CONFIG.GUESS_ROUND_SECONDS;

/** Show the sign-in prompt at most once per browser session. */
function tryPromptSignIn(set: (v: boolean) => void) {
  if (!sessionStorage.getItem("sign_in_prompted")) {
    sessionStorage.setItem("sign_in_prompted", "1");
    set(true);
  }
}

// ── Autocomplete hook ──────────────────────────────────────────────────────────
function useCricketerSearch(query: string) {
  const [results, setResults] = useState<{ id: number; name: string; country: string | null }[]>([]);
  const [loading, setLoading] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    if (query.length < 2) { setResults([]); return; }
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await api.searchCricketers(query);
        setResults(data);
      } catch { setResults([]); }
      finally { setLoading(false); }
    }, 200);
    return () => clearTimeout(timeoutRef.current);
  }, [query]);

  return { results, loading };
}

// ── Main component ────────────────────────────────────────────────────────────
function GuessGame() {
  const [phase, setPhase] = useState<"setup" | "loading" | "error" | "playing" | "done">("setup");
  const [sets, setSets] = useState<GameSet[]>([]);
  const [selectedSetId, setSelectedSetId] = useState<number | null>(null); // null = All
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [questions, setQuestions] = useState<SessionQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [correct, setCorrect] = useState(0);
  const [seconds, setSeconds] = useState<number>(ROUND_SECONDS);
  const [typed, setTyped] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [hintIndex, setHintIndex] = useState(0);
  const [hints, setHints] = useState<string[]>([]);
  const [lastResult, setLastResult] = useState<AnswerResult | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [promptSignIn, setPromptSignIn] = useState(false);
  const [finalResult, setFinalResult] = useState<{ score: number; correct: number; total: number } | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const inputRef = useRef<HTMLInputElement>(null);

  const { results: suggestions } = useCricketerSearch(showDropdown ? typed : "");

  const TOTAL = questions.length;
  const currentQ = questions[index];

  // ── Fetch sets for the picker ──────────────────────────────────────────────
  useEffect(() => {
    api.listGameSets(GAME_SLUG)
      .then(setSets)
      .catch(() => {/* ignore — just skip the picker */});
  }, []);

  // ── Start session ───────────────────────────────────────────────────────────
  function startGame(setId: number | null) {
    setPhase("loading");
    const guestToken = localStorage.getItem("boh_guest_token") ?? (() => {
      const t = crypto.randomUUID();
      localStorage.setItem("boh_guest_token", t);
      return t;
    })();

    // Read IDs played so far this browser session to avoid repeats
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
    if (seconds <= 0) { handleTimeUp(); return; }
    const t = setTimeout(() => setSeconds((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [seconds, phase, showResult]);

  // ── Helpers ────────────────────────────────────────────────────────────────
  async function handleTimeUp() { await submitAnswer("", true); }

  async function submitAnswer(answer: string, timedOut = false) {
    if (!sessionId || !currentQ || showResult) return;
    const elapsed = Math.round(Date.now() - startTimeRef.current);
    setShowDropdown(false);

    try {
      const result = await api.submitAnswer(sessionId, {
        question_id: currentQ.id,
        ...(timedOut ? {} : { answer_given: answer }),
        response_time_ms: elapsed,
        hints_used: hintIndex,
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

  function advanceQuestion(result: AnswerResult | null) {
    void result;
    setShowResult(false);
    setLastResult(null);
    setTyped("");
    setHintIndex(0);
    setHints([]);
    startTimeRef.current = Date.now();

    const next = index + 1;
    if (next >= TOTAL) {
      // Persist all played question IDs into sessionStorage to avoid repeats
      const playedKey = `played_qids_${GAME_SLUG}`;
      const prev: number[] = JSON.parse(sessionStorage.getItem(playedKey) ?? "[]");
      const newIds = questions.map((q) => q.id);
      const merged = Array.from(new Set([...prev, ...newIds]));
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
    if (!sessionId || !currentQ) return;
    try {
      const result = await api.getHint(sessionId, currentQ.id, hintIndex);
      if (result.hint) {
        setHints((h) => [...h, result.hint!]);
        setHintIndex((i) => i + 1);
      }
    } catch { /* no more hints */ }
  }

  // ── Render: Setup (set picker) ─────────────────────────────────────────────
  if (phase === "setup") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-0 bg-background px-4">
        <div className="w-full max-w-sm">
          <p className="text-center text-xs font-bold uppercase tracking-[0.24em] text-muted-foreground mb-2">
            Guess the Cricketer
          </p>
          <div className="rounded-2xl border border-border bg-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Layers className="h-5 w-5 text-muted-foreground" />
              <h2 className="font-display text-2xl">Choose a set</h2>
            </div>

            <div className="grid gap-2">
              {/* All sets — default selection */}
              <button
                onClick={() => { setSelectedSetId(null); }}
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

  // ── Render: Loading ────────────────────────────────────────────────────────
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
            gameName: "Guess the Cricketer",
            score: finalResult.score,
            correct: finalResult.correct,
            total: finalResult.total,
            streak: 0,
            otherGameName: "Unscramble",
            otherGamePath: "/play/unscramble",
            replayPath: "/play/guess",
          }}
        />
        <SignInSheet open={promptSignIn} onDismiss={() => setPromptSignIn(false)} />
        <BottomNav />
      </main>
    );
  }

  if (!currentQ) return null;

  const pct = (seconds / ROUND_SECONDS) * 100;
  const hintCount = currentQ.hint_count ?? 0;

  return (
    <main className="min-h-screen pb-28 md:pt-20 md:pb-10">
      <div className="mx-auto w-full max-w-md px-4 md:max-w-2xl md:px-6">

        {/* HUD */}
        <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 pt-4">
          <Link to="/" aria-label="Quit" className="grid h-11 w-11 place-items-center rounded-full bg-secondary text-secondary-foreground">
            <X className="h-5 w-5" />
          </Link>
          <div className="text-center">
            <div className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
              {index + 1}/{TOTAL}
            </div>
            <div className="mt-1 flex gap-1">
              {Array.from({ length: TOTAL }).map((_, i) => (
                <span key={i} className={`h-1.5 flex-1 rounded-full ${i < index ? "bg-primary" : i === index ? "bg-accent" : "bg-muted"}`} />
              ))}
            </div>
          </div>
          <div className="rounded-lg px-2.5 py-1.5 scoreboard-panel">
            <span className="font-score text-xl leading-none">{score}</span>
          </div>
        </div>

        {/* Timer */}
        <div className="mt-4 h-3 overflow-hidden rounded-full bg-muted">
          <div
            className={`h-full rounded-full transition-[width] duration-1000 ease-linear ${seconds <= 5 ? "bg-destructive" : "bg-accent"}`}
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Image clue — object-contain so full image is always visible */}
        <div className="mt-4 overflow-hidden rounded-2xl border border-border bg-pitch grain">
          {currentQ.image_url ? (
            <img
              src={currentQ.image_url}
              alt="Mystery cricketer"
              className="mx-auto block max-h-80 w-full object-contain md:max-h-[28rem]"
              draggable={false}
              onContextMenu={(e) => e.preventDefault()}
            />
          ) : (
            <div className="flex h-56 items-center justify-center text-muted-foreground">
              <span className="text-6xl">🏏</span>
            </div>
          )}
        </div>

        {/* Result feedback */}
        {showResult && lastResult && (
          <div className={`mt-4 rounded-xl border-2 p-4 ${lastResult.is_correct ? "border-green-500 bg-green-500/10" : "border-destructive bg-destructive/10"}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-display text-xl">
                  {lastResult.is_correct ? "✅ Correct!" : "❌ Not quite"}
                </p>
                {lastResult.correct_answer && !lastResult.is_correct && (
                  <p className="mt-1 text-sm text-muted-foreground">
                    Answer: <strong>{lastResult.correct_answer}</strong>
                  </p>
                )}
                {lastResult.explanation && (
                  <p className="mt-1 text-xs text-muted-foreground">{lastResult.explanation}</p>
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

        {/* Hints */}
        {hints.length > 0 && (
          <ul className="mt-3 grid gap-1.5">
            {hints.map((h, i) => (
              <li key={i} className="rounded-lg bg-secondary px-3 py-2 text-sm font-semibold text-secondary-foreground">
                💡 {h}
              </li>
            ))}
          </ul>
        )}

        {/* Answer input with autocomplete */}
        {!showResult && (
          <div className="relative mt-4">
            <input
              ref={inputRef}
              value={typed}
              onChange={(e) => {
                setTyped(e.target.value);
                setShowDropdown(true);
              }}
              onFocus={() => typed.length >= 2 && setShowDropdown(true)}
              onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && typed.trim()) submitAnswer(typed.trim());
              }}
              placeholder="Type the cricketer's name…"
              autoComplete="off"
              spellCheck={false}
              className="w-full min-h-[60px] rounded-xl border border-input bg-card px-4 text-lg outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
            />
            {showDropdown && suggestions.length > 0 && (
              <ul className="absolute left-0 right-0 top-full z-20 mt-1 max-h-52 overflow-y-auto rounded-xl border border-border bg-card shadow-lg">
                {suggestions.map((s) => (
                  <li key={s.id}>
                    <button
                      className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-secondary"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        setTyped(s.name);
                        setShowDropdown(false);
                        submitAnswer(s.name);
                      }}
                    >
                      {s.country && (
                        <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[11px] font-bold tracking-wider text-muted-foreground">
                          {s.country}
                        </span>
                      )}
                      <span className="font-display text-lg">{s.name}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Actions */}
        {!showResult && (
          <div className="mt-3 grid grid-cols-2 gap-2.5">
            <button
              disabled={!typed.trim()}
              onClick={() => submitAnswer(typed.trim())}
              className="min-h-[52px] rounded-xl bg-primary px-4 font-display text-lg tracking-wide text-primary-foreground tile-press disabled:opacity-40"
            >
              Lock it in
            </button>
            <button
              disabled={hintIndex >= hintCount}
              onClick={handleHint}
              className="flex min-h-[52px] items-center justify-center gap-2 rounded-xl border border-dashed border-border text-sm font-bold text-muted-foreground disabled:opacity-40"
            >
              <Lightbulb className="h-4 w-4" /> Hint ({hintCount - hintIndex} left)
            </button>
          </div>
        )}
      </div>
      <BottomNav />
    </main>
  );
}
