/**
 * Content Admin Panel — /admin
 * Password-protected via HTTP Basic Auth (stored in memory only, never persisted).
 * Allows managing questions, images, and the cricketers list.
 */
import React, { useState, useEffect, useRef } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Eye, EyeOff, Trash2, Plus, Upload, LogOut, Loader2, Check, X, Pencil } from "lucide-react";
import {
  api,
  type AdminGame,
  type QuestionSetItem,
  type AdminQuestion,
  type CricketerItem,
} from "@/lib/api";

export const Route = createFileRoute("/admin")({
  component: AdminPanel,
});

// ── Small helpers ──────────────────────────────────────────────────────────────

function useAdminState() {
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [authed, setAuthed] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [loggingIn, setLoggingIn] = useState(false);

  async function login() {
    setLoggingIn(true);
    setLoginError("");
    try {
      // A quick probe — listing games is a cheap authed endpoint
      await api.admin.listGames(u, p);
      setAuthed(true);
    } catch (e: unknown) {
      const msg = (e as Error).message;
      setLoginError(msg === "UNAUTHORIZED" ? "Wrong username or password." : msg);
    } finally {
      setLoggingIn(false);
    }
  }

  function logout() {
    setAuthed(false);
    setU("");
    setP("");
  }

  return { u, setU, p, setP, authed, loginError, loggingIn, login, logout };
}

// ── Login Screen ───────────────────────────────────────────────────────────────

function LoginScreen({
  u, setU, p, setP, login, loggingIn, loginError,
}: ReturnType<typeof useAdminState>) {
  const [showPass, setShowPass] = useState(false);

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 shadow-lg">
        <div className="text-center">
          <span className="text-4xl">🏏</span>
          <h1 className="mt-3 font-display text-3xl">Admin Panel</h1>
          <p className="mt-1 text-sm text-muted-foreground">Content management only</p>
        </div>
        <div className="mt-6 grid gap-3">
          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Username
            </label>
            <input
              value={u}
              onChange={(e) => setU(e.target.value)}
              autoComplete="username"
              className="w-full rounded-xl border border-input bg-background px-4 py-3 text-base outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Password
            </label>
            <div className="relative">
              <input
                type={showPass ? "text" : "password"}
                value={p}
                onChange={(e) => setP(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && login()}
                autoComplete="current-password"
                className="w-full rounded-xl border border-input bg-background px-4 py-3 pr-12 text-base outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
              />
              <button
                type="button"
                onClick={() => setShowPass((s) => !s)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground"
              >
                {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          {loginError && (
            <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm font-semibold text-destructive">
              {loginError}
            </p>
          )}
          <button
            onClick={login}
            disabled={!u || !p || loggingIn}
            className="flex min-h-[52px] items-center justify-center gap-2 rounded-xl bg-primary font-display text-xl tracking-wide text-primary-foreground disabled:opacity-50"
          >
            {loggingIn ? <Loader2 className="h-5 w-5 animate-spin" /> : "Sign in"}
          </button>
        </div>
      </div>
    </main>
  );
}

// ── Main panel ─────────────────────────────────────────────────────────────────

function AdminPanel() {
  const auth = useAdminState();

  if (!auth.authed) return <LoginScreen {...auth} />;

  return <DashboardShell u={auth.u} p={auth.p} onLogout={auth.logout} />;
}

function DashboardShell({ u, p, onLogout }: { u: string; p: string; onLogout: () => void }) {
  const [tab, setTab] = useState<"guess" | "unscramble" | "cricketers">("guess");

  return (
    <div className="min-h-screen bg-background">
      {/* Top bar */}
      <header className="sticky top-0 z-10 border-b border-border bg-card px-4 py-3 md:px-6">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <span className="font-display text-2xl">🏏 Admin</span>
          <button
            onClick={onLogout}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm font-semibold text-muted-foreground hover:bg-secondary"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-5xl gap-0 px-4 md:px-6">
          {(["guess", "unscramble", "cricketers"] as const).map((t) => {
            const labels = { guess: "Guess the Cricketer", unscramble: "Unscramble", cricketers: "Cricketers List" };
            return (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`border-b-2 px-4 py-3 text-sm font-bold transition-colors ${
                  tab === t ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                {labels[t]}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mx-auto max-w-5xl px-4 py-6 md:px-6">
        {tab === "guess" && <GuessTab u={u} p={p} />}
        {tab === "unscramble" && <UnscrambleTab u={u} p={p} />}
        {tab === "cricketers" && <CricketersTab u={u} p={p} />}
      </div>
    </div>
  );
}

// ── Shared ─────────────────────────────────────────────────────────────────────

function useGameSets(u: string, p: string, slug: string) {
  const [sets, setSets] = useState<QuestionSetItem[]>([]);
  const [selectedSet, setSelectedSet] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [newSetName, setNewSetName] = useState("");

  useEffect(() => {
    api.admin.listSets(u, p, slug).then((data) => {
      setSets(data);
      if (data.length > 0) setSelectedSet(data[0]?.id ?? null);
    }).catch(() => {});
  }, [u, p, slug]);

  async function createSet() {
    if (!newSetName.trim()) return;
    setCreating(true);
    try {
      const s = await api.admin.createSet(u, p, slug, newSetName.trim());
      setSets((prev) => [...prev, { id: s.id, name: s.name, is_active: true, difficulty: "medium" }]);
      setSelectedSet(s.id);
      setNewSetName("");
    } catch { /* ignore */ }
    setCreating(false);
  }

  return { sets, selectedSet, setSelectedSet, newSetName, setNewSetName, creating, createSet };
}

function SetSelector({
  sets, selectedSet, setSelectedSet,
  newSetName, setNewSetName, creating, createSet,
}: ReturnType<typeof useGameSets>) {
  return (
    <div className="mb-6 rounded-xl border border-border bg-card p-4">
      <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-muted-foreground">Question Set</h3>
      <div className="flex flex-wrap gap-2">
        {sets.map((s) => (
          <button
            key={s.id}
            onClick={() => setSelectedSet(s.id)}
            className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
              selectedSet === s.id ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
            }`}
          >
            {s.name}
          </button>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <input
          value={newSetName}
          onChange={(e) => setNewSetName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && createSet()}
          placeholder="New set name…"
          className="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-ring"
        />
        <button
          onClick={createSet}
          disabled={!newSetName.trim() || creating}
          className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-bold text-primary-foreground disabled:opacity-40"
        >
          {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          Create
        </button>
      </div>
    </div>
  );
}

// Inline toast-style feedback
function Feedback({ ok, msg }: { ok: boolean | null; msg: string }) {
  if (!msg) return null;
  return (
    <div className={`flex items-center gap-2 rounded-xl border-2 px-4 py-3 text-sm font-semibold ${ok ? "border-green-500 bg-green-500/10 text-green-700" : "border-destructive bg-destructive/10 text-destructive"}`}>
      {ok ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />} {msg}
    </div>
  );
}

// ── Edit forms ─────────────────────────────────────────────────────────────────

function EditGuessQuestionForm({
  u, p, question, onSave, onCancel,
}: {
  u: string; p: string;
  question: AdminQuestion;
  onSave: (updated: AdminQuestion) => void;
  onCancel: () => void;
}) {
  const [answer, setAnswer] = useState(question.correct_answer ?? "");
  const [aliases, setAliases] = useState(question.aliases.join(", "));
  const [difficulty, setDifficulty] = useState(question.difficulty);
  const [points, setPoints] = useState(String(question.points ?? 100));
  const [explanation, setExplanation] = useState(question.explanation ?? "");
  const [isActive, setIsActive] = useState(question.is_active);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      let imageUrl: string | undefined;
      if (imageFile) {
        const { url } = await api.admin.uploadImage(u, p, imageFile);
        imageUrl = url;
      }
      const updated = await api.admin.updateQuestion(u, p, question.id, {
        ...(answer.trim() !== (question.correct_answer ?? "") ? { answer: answer.trim() } : {}),
        ...(imageUrl ? { image_url: imageUrl } : {}),
        aliases: aliases.split(",").map((a) => a.trim()).filter(Boolean),
        difficulty,
        ...(explanation.trim() ? { explanation: explanation.trim() } : {}),
        is_active: isActive,
      });
      onSave(updated);
    } catch (e: unknown) {
      setError((e as Error).message);
    }
    setSaving(false);
  }

  return (
    <div className="rounded-xl border-2 border-primary/30 bg-primary/5 p-4 grid gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-widest text-primary">Editing question #{question.id}</span>
        <button onClick={onCancel} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
      </div>

      {/* Image */}
      <div>
        <div className="flex gap-3 items-start">
          {(imageFile ? URL.createObjectURL(imageFile) : question.image_url) && (
            <img
              src={imageFile ? URL.createObjectURL(imageFile) : question.image_url!}
              alt=""
              className="h-16 w-16 rounded-lg object-contain border border-border"
            />
          )}
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="flex items-center gap-1.5 rounded-lg border border-dashed border-border px-3 py-2 text-xs font-semibold text-muted-foreground hover:border-primary"
          >
            <Upload className="h-3.5 w-3.5" /> {imageFile ? imageFile.name : "Replace image"}
          </button>
          <input ref={fileRef} type="file" accept="image/*" className="hidden"
            onChange={(e) => setImageFile(e.target.files?.[0] ?? null)} />
        </div>
      </div>

      <Field label="Answer">
        <input value={answer} onChange={(e) => setAnswer(e.target.value)}
          className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-ring" />
      </Field>
      <Field label="Aliases (comma-separated)">
        <input value={aliases} onChange={(e) => setAliases(e.target.value)}
          placeholder="King Kohli, Kohli"
          className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-ring" />
      </Field>
      <Field label="Explanation">
        <input value={explanation} onChange={(e) => setExplanation(e.target.value)}
          className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-ring" />
      </Field>
      <div className="grid grid-cols-3 gap-3">
        <Field label="Difficulty">
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}
            className="w-full rounded-lg border border-input bg-background px-2 py-2 text-sm outline-none">
            {["easy", "medium", "hard"].map((d) => <option key={d}>{d}</option>)}
          </select>
        </Field>
        <Field label="Points">
          <input type="number" value={points} onChange={(e) => setPoints(e.target.value)}
            className="w-full rounded-lg border border-input bg-background px-2 py-2 text-sm outline-none" />
        </Field>
        <Field label="Active">
          <button
            onClick={() => setIsActive((v) => !v)}
            className={`mt-1 rounded-lg px-3 py-2 text-xs font-bold ${isActive ? "bg-green-500/20 text-green-700" : "bg-muted text-muted-foreground"}`}
          >
            {isActive ? "Yes" : "No"}
          </button>
        </Field>
      </div>

      {error && <p className="text-xs font-semibold text-destructive">{error}</p>}

      <div className="flex gap-2 justify-end">
        <button onClick={onCancel} className="rounded-lg border border-border px-4 py-2 text-sm font-semibold">Cancel</button>
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-bold text-primary-foreground disabled:opacity-40">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          Save
        </button>
      </div>
    </div>
  );
}

function EditUnscrambleQuestionForm({
  u, p, question, onSave, onCancel,
}: {
  u: string; p: string;
  question: AdminQuestion;
  onSave: (updated: AdminQuestion) => void;
  onCancel: () => void;
}) {
  const [countryStr, roleStr] = (question.question_text ?? "").split("|");
  const [answer, setAnswer] = useState(question.correct_answer ?? "");
  const [country, setCountry] = useState(countryStr?.trim() ?? "");
  const [role, setRole] = useState(roleStr?.trim() ?? "");
  const [hints, setHints] = useState<string[]>(
    question.aliases.length > 0 ? [...question.aliases, "", ""].slice(0, 3) : ["", "", ""]
  );
  const [difficulty, setDifficulty] = useState(question.difficulty);
  const [isActive, setIsActive] = useState(question.is_active);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const updated = await api.admin.updateQuestion(u, p, question.id, {
        ...(answer.trim() !== (question.correct_answer ?? "") ? { answer: answer.trim() } : {}),
        country: country.trim(),
        role: role.trim(),
        aliases: hints.filter((h) => h.trim()),
        difficulty,
        is_active: isActive,
      });
      onSave(updated);
    } catch (e: unknown) {
      setError((e as Error).message);
    }
    setSaving(false);
  }

  return (
    <div className="rounded-xl border-2 border-primary/30 bg-primary/5 p-4 grid gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-widest text-primary">Editing question #{question.id}</span>
        <button onClick={onCancel} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
      </div>

      <Field label="Cricketer Name (Answer)">
        <input value={answer} onChange={(e) => setAnswer(e.target.value)}
          className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-ring uppercase" />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Country Code">
          <input value={country} onChange={(e) => setCountry(e.target.value.toUpperCase())} maxLength={4}
            className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-ring" />
        </Field>
        <Field label="Role">
          <select value={role} onChange={(e) => setRole(e.target.value)}
            className="w-full rounded-lg border border-input bg-background px-2 py-2 text-sm outline-none">
            <option value="">Select…</option>
            {["Batter", "Bowler", "All-rounder", "Wicket-keeper", "Opening batter"].map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        </Field>
      </div>

      <div>
        <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
          Hints (shown one at a time after Country/Role)
        </label>
        {hints.map((h, i) => (
          <input key={i} value={h} placeholder={`Hint ${i + 1}`}
            onChange={(e) => setHints((arr) => arr.map((x, j) => j === i ? e.target.value : x))}
            className="mb-2 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-ring" />
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Difficulty">
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}
            className="w-full rounded-lg border border-input bg-background px-2 py-2 text-sm outline-none">
            {["easy", "medium", "hard"].map((d) => <option key={d}>{d}</option>)}
          </select>
        </Field>
        <Field label="Active">
          <button onClick={() => setIsActive((v) => !v)}
            className={`mt-1 rounded-lg px-3 py-2 text-xs font-bold ${isActive ? "bg-green-500/20 text-green-700" : "bg-muted text-muted-foreground"}`}>
            {isActive ? "Yes" : "No"}
          </button>
        </Field>
      </div>

      {error && <p className="text-xs font-semibold text-destructive">{error}</p>}

      <div className="flex gap-2 justify-end">
        <button onClick={onCancel} className="rounded-lg border border-border px-4 py-2 text-sm font-semibold">Cancel</button>
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-bold text-primary-foreground disabled:opacity-40">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          Save
        </button>
      </div>
    </div>
  );
}

/** Small label+children wrapper used inside edit forms */
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

// ── Guess the Cricketer Tab ───────────────────────────────────────────────────

function GuessTab({ u, p }: { u: string; p: string }) {
  const setsData = useGameSets(u, p, "guess-the-cricketer");
  const { selectedSet } = setsData;
  const [questions, setQuestions] = useState<AdminQuestion[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [answer, setAnswer] = useState("");
  const [aliases, setAliases] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [points, setPoints] = useState("100");
  const [explanation, setExplanation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ ok: boolean; msg: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!selectedSet) return;
    api.admin.listQuestions(u, p, "guess-the-cricketer", selectedSet)
      .then(setQuestions).catch(() => {});
  }, [u, p, selectedSet]);

  function clearFeedback() { setTimeout(() => setFeedback(null), 4000); }

  async function handleSubmit() {
    if (!selectedSet || !imageFile || !answer.trim()) return;
    setSubmitting(true);
    setFeedback(null);
    try {
      const { url } = await api.admin.uploadImage(u, p, imageFile);
      await api.admin.addImageGuessQuestion(u, p, {
        game_slug: "guess-the-cricketer",
        set_id: selectedSet!,
        image_url: url,
        answer: answer.trim(),
        ...(aliases.trim() ? { aliases: aliases.trim() } : {}),
        difficulty,
        points: Number(points),
        ...(explanation.trim() ? { explanation: explanation.trim() } : {}),
      });
      setFeedback({ ok: true, msg: `Added "${answer.trim()}" successfully.` });
      setImageFile(null);
      setAnswer("");
      setAliases("");
      setExplanation("");
      if (fileRef.current) fileRef.current.value = "";
      // Refresh list
      api.admin.listQuestions(u, p, "guess-the-cricketer", selectedSet)
        .then(setQuestions).catch(() => {});
    } catch (e: unknown) {
      setFeedback({ ok: false, msg: (e as Error).message });
    }
    setSubmitting(false);
    clearFeedback();
  }

  async function deleteQuestion(id: number) {
    if (!confirm("Delete this question?")) return;
    try {
      await api.admin.deleteQuestion(u, p, id);
      setQuestions((q) => q.filter((x) => x.id !== id));
    } catch { /* ignore */ }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Add question */}
      <div className="rounded-2xl border border-border bg-card p-5">
        <h2 className="mb-4 font-display text-2xl">Add Image Question</h2>
        <SetSelector {...setsData} />

        {/* Image upload */}
        <div
          className="mb-3 cursor-pointer rounded-xl border-2 border-dashed border-border bg-muted p-6 text-center hover:border-primary"
          onClick={() => fileRef.current?.click()}
        >
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => setImageFile(e.target.files?.[0] ?? null)}
          />
          {imageFile ? (
            <div className="space-y-1">
              <img
                src={URL.createObjectURL(imageFile)}
                alt="Preview"
                className="mx-auto max-h-48 rounded-xl object-contain"
              />
              <p className="text-xs text-muted-foreground">{imageFile.name}</p>
            </div>
          ) : (
            <div className="space-y-2">
              <Upload className="mx-auto h-8 w-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Click to upload image<br />(face, stance, action, etc.)</p>
            </div>
          )}
        </div>

        <div className="grid gap-3">
          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Correct Answer *
            </label>
            <input
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="e.g. Virat Kohli"
              className="w-full rounded-xl border border-input bg-background px-4 py-2.5 text-base outline-none focus:border-ring"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Accepted Aliases
            </label>
            <input
              value={aliases}
              onChange={(e) => setAliases(e.target.value)}
              placeholder="King Kohli, Kohli (comma-separated)"
              className="w-full rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus:border-ring"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Explanation (optional)
            </label>
            <input
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              placeholder="Shown after answer is revealed"
              className="w-full rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus:border-ring"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">Difficulty</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm outline-none"
              >
                {["easy", "medium", "hard"].map((d) => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">Points</label>
              <input
                type="number"
                value={points}
                onChange={(e) => setPoints(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm outline-none"
              />
            </div>
          </div>
        </div>

        {feedback && <div className="mt-4"><Feedback ok={feedback.ok} msg={feedback.msg} /></div>}

        <button
          onClick={handleSubmit}
          disabled={!selectedSet || !imageFile || !answer.trim() || submitting}
          className="mt-4 flex w-full min-h-[52px] items-center justify-center gap-2 rounded-xl bg-primary font-display text-xl tracking-wide text-primary-foreground disabled:opacity-40"
        >
          {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <><Plus className="h-5 w-5" /> Add Question</>}
        </button>
      </div>

      {/* Questions list */}
      <div className="rounded-2xl border border-border bg-card p-5">
        <h2 className="mb-4 font-display text-2xl">Questions ({questions.length})</h2>
        {questions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No questions in this set yet. Add some on the left.</p>
        ) : (
          <ul className="grid gap-3">
            {questions.map((q) =>
              editingId === q.id ? (
                <li key={q.id}>
                  <EditGuessQuestionForm
                    u={u} p={p} question={q}
                    onSave={(updated) => {
                      setQuestions((prev) => prev.map((x) => x.id === updated.id ? { ...x, ...updated } : x));
                      setEditingId(null);
                    }}
                    onCancel={() => setEditingId(null)}
                  />
                </li>
              ) : (
                <li key={q.id} className="flex items-center gap-3 rounded-xl border border-border p-3">
                  {q.image_url && (
                    <img src={q.image_url} alt="" className="h-14 w-14 shrink-0 rounded-lg object-contain" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold">{q.correct_answer ?? "—"}</p>
                    <p className="text-xs text-muted-foreground">{q.difficulty} · {q.is_active ? "active" : "inactive"}</p>
                    {q.aliases.length > 0 && (
                      <p className="text-xs text-muted-foreground">also: {q.aliases.join(", ")}</p>
                    )}
                  </div>
                  <button
                    onClick={() => setEditingId(q.id)}
                    className="shrink-0 rounded-lg p-2 text-muted-foreground hover:bg-secondary"
                    title="Edit"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => deleteQuestion(q.id)}
                    className="shrink-0 rounded-lg p-2 text-destructive hover:bg-destructive/10"
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </li>
              )
            )}
          </ul>
        )}
      </div>
    </div>
  );
}

// ── Unscramble Tab ────────────────────────────────────────────────────────────

function UnscrambleTab({ u, p }: { u: string; p: string }) {
  const setsData = useGameSets(u, p, "unscramble-the-name");
  const { selectedSet } = setsData;
  const [questions, setQuestions] = useState<AdminQuestion[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [wordAnswer, setWordAnswer] = useState("");
  const [country, setCountry] = useState("");
  const [role, setRole] = useState("");
  const [hints, setHints] = useState(["", "", ""]);
  const [difficulty, setDifficulty] = useState("medium");
  const [points, setPoints] = useState("100");
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ ok: boolean; msg: string } | null>(null);

  useEffect(() => {
    if (!selectedSet) return;
    api.admin.listQuestions(u, p, "unscramble-the-name", selectedSet)
      .then(setQuestions).catch(() => {});
  }, [u, p, selectedSet]);

  function clearFeedback() { setTimeout(() => setFeedback(null), 4000); }

  async function handleSubmit() {
    if (!selectedSet || !wordAnswer.trim() || !country.trim() || !role.trim()) return;
    setSubmitting(true);
    setFeedback(null);
    try {
      await api.admin.addUnscrambleQuestion(u, p, {
        game_slug: "unscramble-the-name",
        set_id: selectedSet,
        answer: wordAnswer.trim(),
        country: country.trim(),
        role: role.trim(),
        difficulty,
        points: Number(points),
        hints: hints.filter((h) => h.trim()),
      });
      setFeedback({ ok: true, msg: `Added "${wordAnswer.trim()}" successfully.` });
      setWordAnswer("");
      setCountry("");
      setRole("");
      setHints(["", "", ""]);
      api.admin.listQuestions(u, p, "unscramble-the-name", selectedSet)
        .then(setQuestions).catch(() => {});
    } catch (e: unknown) {
      setFeedback({ ok: false, msg: (e as Error).message });
    }
    setSubmitting(false);
    clearFeedback();
  }

  async function deleteQuestion(id: number) {
    if (!confirm("Delete this question?")) return;
    try {
      await api.admin.deleteQuestion(u, p, id);
      setQuestions((q) => q.filter((x) => x.id !== id));
    } catch { /* ignore */ }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Add question */}
      <div className="rounded-2xl border border-border bg-card p-5">
        <h2 className="mb-4 font-display text-2xl">Add Unscramble Question</h2>
        <SetSelector {...setsData} />

        <div className="grid gap-3">
          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Cricketer's Name (Answer) *
            </label>
            <input
              value={wordAnswer}
              onChange={(e) => setWordAnswer(e.target.value)}
              placeholder="e.g. SACHIN TENDULKAR"
              className="w-full rounded-xl border border-input bg-background px-4 py-2.5 text-base outline-none focus:border-ring"
            />
            {wordAnswer && (
              <p className="mt-1 text-xs text-muted-foreground">
                Letters ({wordAnswer.replace(/\s/g, "").length}): {wordAnswer.toUpperCase().replace(/\s/g, "").split("").join(" · ")}
              </p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Country Code * <span className="normal-case font-normal">(IND, AUS…)</span>
              </label>
              <input
                value={country}
                onChange={(e) => setCountry(e.target.value.toUpperCase())}
                maxLength={4}
                placeholder="IND"
                className="w-full rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus:border-ring"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">Role *</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm outline-none"
              >
                <option value="">Select…</option>
                {["Batter", "Bowler", "All-rounder", "Wicket-keeper", "Opening batter"].map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Hints */}
          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Hints (optional, shown one at a time)
            </label>
            {hints.map((h, i) => (
              <input
                key={i}
                value={h}
                onChange={(e) => setHints((arr) => arr.map((x, j) => j === i ? e.target.value : x))}
                placeholder={`Hint ${i + 1}`}
                className="mb-2 w-full rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus:border-ring"
              />
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">Difficulty</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm outline-none"
              >
                {["easy", "medium", "hard"].map((d) => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">Points</label>
              <input
                type="number"
                value={points}
                onChange={(e) => setPoints(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm outline-none"
              />
            </div>
          </div>
        </div>

        {feedback && <div className="mt-4"><Feedback ok={feedback.ok} msg={feedback.msg} /></div>}

        <button
          onClick={handleSubmit}
          disabled={!selectedSet || !wordAnswer.trim() || !country.trim() || !role || submitting}
          className="mt-4 flex w-full min-h-[52px] items-center justify-center gap-2 rounded-xl bg-primary font-display text-xl tracking-wide text-primary-foreground disabled:opacity-40"
        >
          {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <><Plus className="h-5 w-5" /> Add Question</>}
        </button>
      </div>

      {/* Questions list */}
      <div className="rounded-2xl border border-border bg-card p-5">
        <h2 className="mb-4 font-display text-2xl">Questions ({questions.length})</h2>
        {questions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No questions in this set yet.</p>
        ) : (
          <ul className="grid gap-3">
            {questions.map((q) => {
              const [qCountry, qRole] = (q.question_text ?? "").split("|");
              return editingId === q.id ? (
                <li key={q.id}>
                  <EditUnscrambleQuestionForm
                    u={u} p={p} question={q}
                    onSave={(updated) => {
                      setQuestions((prev) => prev.map((x) => x.id === updated.id ? { ...x, ...updated } : x));
                      setEditingId(null);
                    }}
                    onCancel={() => setEditingId(null)}
                  />
                </li>
              ) : (
                <li key={q.id} className="flex items-center gap-3 rounded-xl border border-border p-3">
                  <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-primary font-display text-sm text-primary-foreground">
                    {qCountry || "?"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold">{q.correct_answer ?? "—"}</p>
                    <p className="text-xs text-muted-foreground">{qRole} · {q.difficulty} · {q.is_active ? "active" : "inactive"}</p>
                    {q.aliases.length > 0 && (
                      <p className="text-xs text-muted-foreground">hints: {q.aliases.join(" / ")}</p>
                    )}
                  </div>
                  <button
                    onClick={() => setEditingId(q.id)}
                    className="shrink-0 rounded-lg p-2 text-muted-foreground hover:bg-secondary"
                    title="Edit"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => deleteQuestion(q.id)}
                    className="shrink-0 rounded-lg p-2 text-destructive hover:bg-destructive/10"
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

// ── Cricketers List Tab ───────────────────────────────────────────────────────

function CricketersTab({ u, p }: { u: string; p: string }) {
  const [cricketers, setCricketers] = useState<CricketerItem[]>([]);
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [adding, setAdding] = useState(false);
  const [search, setSearch] = useState("");
  const [feedback, setFeedback] = useState<{ ok: boolean; msg: string } | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editCountry, setEditCountry] = useState("");
  const [editSaving, setEditSaving] = useState(false);

  useEffect(() => {
    api.admin.listCricketers(u, p).then(setCricketers).catch(() => {});
  }, [u, p]);

  function clearFeedback() { setTimeout(() => setFeedback(null), 4000); }

  async function handleAdd() {
    if (!name.trim() || !country.trim()) return;
    setAdding(true);
    try {
      const c = await api.admin.addCricketer(u, p, name.trim(), country.trim().toUpperCase());
      setCricketers((prev) => [...prev, { id: c.id, name: c.name, country: country.trim().toUpperCase() }]);
      setName("");
      setCountry("");
      setFeedback({ ok: true, msg: `${c.name} added.` });
    } catch (e: unknown) {
      setFeedback({ ok: false, msg: (e as Error).message });
    }
    setAdding(false);
    clearFeedback();
  }

  async function handleDelete(id: number, cname: string) {
    if (!confirm(`Remove ${cname} from autocomplete list?`)) return;
    try {
      await api.admin.deleteCricketer(u, p, id);
      setCricketers((c) => c.filter((x) => x.id !== id));
    } catch { /* ignore */ }
  }

  function startEdit(c: CricketerItem) {
    setEditingId(c.id);
    setEditName(c.name);
    setEditCountry(c.country ?? "");
  }

  async function saveEdit(id: number) {
    setEditSaving(true);
    try {
      const updated = await api.admin.updateCricketer(u, p, id, editName.trim(), editCountry.trim().toUpperCase());
      setCricketers((prev) => prev.map((c) => c.id === id ? updated : c));
      setEditingId(null);
    } catch (e: unknown) {
      setFeedback({ ok: false, msg: (e as Error).message });
    }
    setEditSaving(false);
  }

  const filtered = cricketers.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    (c.country ?? "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="mx-auto max-w-2xl">
      <div className="rounded-2xl border border-border bg-card p-5">
        <h2 className="mb-1 font-display text-2xl">Cricketers Autocomplete List</h2>
        <p className="mb-5 text-sm text-muted-foreground">
          This list powers the autocomplete dropdown in the Guess the Cricketer game. The correct answer is never shown to players before they guess.
        </p>

        {/* Add form */}
        <div className="mb-5 grid grid-cols-[1fr_auto_auto] gap-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="Full name, e.g. Rohit Sharma"
            className="rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus:border-ring"
          />
          <input
            value={country}
            onChange={(e) => setCountry(e.target.value.toUpperCase())}
            maxLength={4}
            placeholder="IND"
            className="w-20 rounded-xl border border-input bg-background px-3 py-2.5 text-sm outline-none focus:border-ring"
          />
          <button
            onClick={handleAdd}
            disabled={!name.trim() || !country.trim() || adding}
            className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground disabled:opacity-40"
          >
            {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Add
          </button>
        </div>

        {feedback && <div className="mb-4"><Feedback ok={feedback.ok} msg={feedback.msg} /></div>}

        {/* Search */}
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search existing cricketers…"
          className="mb-3 w-full rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus:border-ring"
        />

        <p className="mb-2 text-xs text-muted-foreground font-semibold">{filtered.length} of {cricketers.length} cricketers</p>

        {/* List */}
        <ul className="grid gap-1.5 max-h-[480px] overflow-y-auto pr-1">
          {filtered.map((c) =>
            editingId === c.id ? (
              <li key={c.id} className="flex items-center gap-2 rounded-xl border-2 border-primary/30 bg-primary/5 px-3 py-2">
                <input
                  value={editCountry}
                  onChange={(e) => setEditCountry(e.target.value.toUpperCase())}
                  maxLength={4}
                  className="w-14 rounded-lg border border-input bg-background px-2 py-1 text-xs outline-none focus:border-ring"
                />
                <input
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && saveEdit(c.id)}
                  className="flex-1 rounded-lg border border-input bg-background px-2 py-1 text-sm outline-none focus:border-ring"
                />
                <button
                  onClick={() => saveEdit(c.id)}
                  disabled={editSaving || !editName.trim()}
                  className="shrink-0 rounded p-1 text-primary hover:bg-primary/10 disabled:opacity-40"
                >
                  {editSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                </button>
                <button onClick={() => setEditingId(null)} className="shrink-0 rounded p-1 text-muted-foreground hover:text-foreground">
                  <X className="h-3.5 w-3.5" />
                </button>
              </li>
            ) : (
              <li key={c.id} className="flex items-center gap-2 rounded-xl border border-border px-3 py-2">
                <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[11px] font-bold tracking-wider text-muted-foreground">
                  {c.country ?? "—"}
                </span>
                <span className="flex-1 font-semibold text-sm">{c.name}</span>
                <button
                  onClick={() => startEdit(c)}
                  className="shrink-0 rounded p-1 text-muted-foreground hover:text-foreground"
                  title="Edit"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => handleDelete(c.id, c.name)}
                  className="shrink-0 rounded p-1 text-muted-foreground hover:text-destructive"
                  title="Delete"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </li>
            )
          )}
        </ul>
      </div>
    </div>
  );
}
