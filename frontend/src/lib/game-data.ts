/**
 * Static metadata for Phase 1 games.
 * Only slugs, display names, hooks, and frontend paths live here.
 * All question data, player counts, and scores come from the API.
 */

export type GameMeta = {
  /** Must match the game slug in the database. */
  id: string;
  name: string;
  hook: string;
  path: string;
};

/** Phase 1 games. Slugs must match rows seeded via scripts/seed.py. */
export const GAMES: GameMeta[] = [
  {
    id: "guess-the-cricketer",
    name: "Guess the Cricketer",
    hook: "One image. Ten seconds. No mercy.",
    path: "/play/guess",
  },
  {
    id: "unscramble-the-name",
    name: "Unscramble the Name",
    hook: "Tap the tiles back into a legend.",
    path: "/play/unscramble",
  },
];
