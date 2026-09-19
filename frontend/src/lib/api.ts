const API_URL = (import.meta.env['VITE_API_URL'] as string | undefined) ?? "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }
  return res.json();
}

// Admin API uses HTTP Basic Auth
function adminHeaders(username: string, password: string): Record<string, string> {
  return {
    Authorization: `Basic ${btoa(`${username}:${password}`)}`,
  };
}

async function adminFetch<T>(
  path: string,
  username: string,
  password: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...adminHeaders(username, password),
      ...options?.headers,
    },
    ...options,
  });
  if (res.status === 401) throw new Error("UNAUTHORIZED");
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }
  return res.json();
}

export const api = {
  // ── Games ─────────────────────────────────────────────────────────────────
  listGames: () => apiFetch<Game[]>("/api/games"),
  getGame: (slug: string) => apiFetch<Game>(`/api/games/${slug}`),
  getGameStats: (slug: string) => apiFetch<GameStats>(`/api/games/${slug}/stats`),
  getDailyChallenge: (slug: string) => apiFetch<DailyInfo>(`/api/games/${slug}/daily`),

  // ── Sessions ──────────────────────────────────────────────────────────────
  startSession: (body: StartSessionBody) =>
    apiFetch<SessionStartResponse>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  submitAnswer: (sessionId: number, body: AnswerBody) =>
    apiFetch<AnswerResult>(`/api/sessions/${sessionId}/answers`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getHint: (sessionId: number, questionId: number, hintIndex: number) =>
    apiFetch<HintResult>(`/api/sessions/${sessionId}/hints/${questionId}?hint_index=${hintIndex}`),
  completeSession: (sessionId: number) =>
    apiFetch<SessionResult>(`/api/sessions/${sessionId}/complete`, { method: "POST" }),

  // ── Leaderboard ───────────────────────────────────────────────────────────
  getLeaderboard: (slug: string, period: "daily" | "all_time" = "all_time") =>
    apiFetch<LeaderboardResponse>(`/api/leaderboards/${slug}?period=${period}`),

  // ── Sets (public) ─────────────────────────────────────────────────────────
  listGameSets: (slug: string) => apiFetch<GameSet[]>(`/api/games/${slug}/sets`),

  // ── Daily ─────────────────────────────────────────────────────────────────
  getTodaysChallenges: () => apiFetch<DailyChallenge[]>("/api/daily"),

  // ── Cricketers (autocomplete) ─────────────────────────────────────────────
  searchCricketers: (q: string) =>
    apiFetch<CricketerMatch[]>(`/api/cricketers/search?q=${encodeURIComponent(q)}`),

  // ── Admin ─────────────────────────────────────────────────────────────────
  admin: {
    listGames: (u: string, p: string) =>
      adminFetch<AdminGame[]>("/api/admin/games", u, p),

    listSets: (u: string, p: string, slug: string) =>
      adminFetch<QuestionSetItem[]>(`/api/admin/games/${slug}/sets`, u, p),

    createSet: (u: string, p: string, slug: string, name: string, difficulty = "medium") =>
      adminFetch<{ id: number; name: string }>(`/api/admin/games/${slug}/sets`, u, p, {
        method: "POST",
        body: JSON.stringify({ name, difficulty, is_active: true }),
      }),

    listQuestions: (u: string, p: string, slug: string, setId?: number) =>
      adminFetch<AdminQuestion[]>(
        `/api/admin/games/${slug}/questions${setId ? `?set_id=${setId}` : ""}`,
        u, p
      ),

    deleteQuestion: (u: string, p: string, id: number) =>
      adminFetch<{ deleted: boolean }>(`/api/admin/questions/${id}`, u, p, { method: "DELETE" }),

    updateQuestion: (u: string, p: string, id: number, data: UpdateQuestionBody) =>
      adminFetch<AdminQuestion>(`/api/admin/questions/${id}`, u, p, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    updateCricketer: (u: string, p: string, id: number, name: string, country: string) =>
      adminFetch<CricketerItem>(`/api/admin/cricketers/${id}`, u, p, {
        method: "PATCH",
        body: JSON.stringify({ name, country }),
      }),

    uploadImage: async (u: string, p: string, file: File): Promise<{ url: string }> => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_URL}/api/admin/upload-image`, {
        method: "POST",
        headers: adminHeaders(u, p),
        body: form,
      });
      if (res.status === 401) throw new Error("UNAUTHORIZED");
      if (!res.ok) throw new Error("Upload failed");
      return res.json();
    },

    addImageGuessQuestion: async (
      u: string, p: string,
      data: {
        game_slug: string; set_id: number; image_url: string;
        answer: string; aliases?: string; difficulty?: string;
        points?: number; explanation?: string;
      }
    ) => {
      const form = new FormData();
      Object.entries(data).forEach(([k, v]) => v != null && form.append(k, String(v)));
      const res = await fetch(`${API_URL}/api/admin/questions/image-guess`, {
        method: "POST",
        headers: adminHeaders(u, p),
        body: form,
      });
      if (res.status === 401) throw new Error("UNAUTHORIZED");
      if (!res.ok) throw new Error("Failed to add question");
      return res.json() as Promise<{ question_id: number; image_url: string }>;
    },

    addUnscrambleQuestion: (
      u: string, p: string,
      data: {
        game_slug: string; set_id: number; answer: string;
        country: string; role: string; difficulty?: string;
        points?: number; hints?: string[];
      }
    ) =>
      adminFetch<{ question_id: number }>("/api/admin/questions/unscramble", u, p, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    listCricketers: (u: string, p: string) =>
      adminFetch<CricketerItem[]>("/api/admin/cricketers", u, p),

    addCricketer: (u: string, p: string, name: string, country: string) =>
      adminFetch<{ id: number; name: string }>("/api/admin/cricketers", u, p, {
        method: "POST",
        body: JSON.stringify({ name, country }),
      }),

    deleteCricketer: (u: string, p: string, id: number) =>
      adminFetch<{ deleted: boolean }>(`/api/admin/cricketers/${id}`, u, p, { method: "DELETE" }),
  },

  // ── Health ────────────────────────────────────────────────────────────────
  health: () => apiFetch<{ status: string }>("/health"),
};

// ── Types ──────────────────────────────────────────────────────────────────────

export type Game = {
  id: number; slug: string; name: string; description: string | null;
  cover_image_url: string | null; config: Record<string, unknown>;
  players_today?: number;
};

export type GameStats = { players_today: number; players_total: number };

export type DailyInfo = { set_id: number; is_scheduled: boolean; date: string };

export type SessionQuestion = {
  id: number;
  type: "image_guess" | "unscramble";
  image_url?: string;
  scrambled_letters?: string[];
  country?: string;
  role?: string;
  points: number;
  hint_count: number;
};

export type StartSessionBody = {
  game_slug: string;
  set_id?: number;
  guest_token?: string;
  is_daily?: boolean;
  exclude_ids?: number[];
};

export type SessionStartResponse = {
  session_id: number;
  game_slug: string;
  total_questions: number;
  questions: SessionQuestion[];
  exhausted?: boolean;  // true when player has seen every available question
};

export type AnswerBody = {
  question_id: number;
  answer_given?: string;
  response_time_ms?: number;
  hints_used?: number;
};

export type AnswerResult = {
  is_correct: boolean;
  points_earned: number;
  correct_answer: string | null;
  explanation: string | null;
};

export type HintResult = { hint: string | null; exhausted: boolean };

export type SessionResult = {
  session_id: number; score: number; accuracy: number;
  correct: number; total: number; share_card_url: string;
};

export type LeaderboardEntry = { rank: number; username: string; score: number; plays: number };
export type LeaderboardResponse = { game: string; period: string; entries: LeaderboardEntry[] };

export type DailyChallenge = { game_slug: string; game_name: string; set_id: number; date: string };

export type GameSet = { id: number; name: string; difficulty: string };
export type CricketerMatch = { id: number; name: string; country: string | null };

export type UpdateQuestionBody = {
  answer?: string;
  image_url?: string;
  aliases?: string[];
  difficulty?: string;
  points?: number;
  explanation?: string;
  is_active?: boolean;
  country?: string;
  role?: string;
};

export type AdminGame = { id: number; slug: string; name: string; status: string };
export type QuestionSetItem = { id: number; name: string; is_active: boolean; difficulty: string };
export type AdminQuestion = {
  id: number; type: string; set_id: number; image_url: string | null;
  question_text: string | null; correct_answer: string | null;
  aliases: string[]; difficulty: string; is_active: boolean; explanation: string | null;
  points: number;
};
export type CricketerItem = { id: number; name: string; country: string | null };
