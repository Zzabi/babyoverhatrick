/**
 * Central game configuration.
 * Change values here — do NOT scatter magic numbers across component files.
 */
export const GAME_CONFIG = {
  // ── Timers (seconds per question) ─────────────────────────────────────────
  GUESS_ROUND_SECONDS: 15,
  UNSCRAMBLE_ROUND_SECONDS: 30,

  // ── Set-picker filter ─────────────────────────────────────────────────────
  // Sets whose name matches this regex are excluded from the individual set
  // picker (they're already included in "All sets").
  DEFAULT_SET_NAME_REGEX: /^default(\s+set)?$/i,

  // ── Autocomplete ──────────────────────────────────────────────────────────
  SEARCH_DEBOUNCE_MS: 200,
  SEARCH_MIN_CHARS: 2,

  // ── Session storage keys ──────────────────────────────────────────────────
  /** Set once after the sign-in prompt fires; prevents it repeating this tab. */
  SIGN_IN_PROMPTED_KEY: "sign_in_prompted",
  /** Prefix for per-game played question ID lists. Append the game slug. */
  PLAYED_QIDS_KEY_PREFIX: "played_qids_",

  // ── Local storage keys ────────────────────────────────────────────────────
  GUEST_TOKEN_KEY: "boh_guest_token",
} as const;
