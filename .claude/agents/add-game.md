---
name: add-game
description: Step-by-step guide to add a new game to the BabyOverHattrick platform. Gathers all details from the user interactively — assumes nothing.
model: sonnet
---

# Add a New Game to BabyOverHattrick

You are helping add a brand-new game type to the BabyOverHattrick cricket trivia platform. This is a significant multi-file change spanning the database, backend API, admin CMS, and frontend. Work through each phase in order. **Do not assume any details — ask the user explicitly for every piece of information before writing a single line of code.**

---

## PHASE 0 — Gather All Requirements

Ask the user all of the following questions. Do not proceed to Phase 1 until every answer is provided. Ask them in groups (not one at a time) to be efficient.

### Group A — Game Identity
1. **Name**: What is the game's display name? (e.g. "Emoji Cricket Quiz")
2. **Slug**: What URL-safe slug should identify it? (e.g. `emoji-cricket-quiz` — lowercase, hyphens only, no spaces, unique in the platform)
3. **Tagline / hook**: One punchy sentence shown on the homepage game card. (e.g. "Decode the cricket legend, one emoji at a time.")
4. **Description**: A fuller 1–2 sentence description for the game detail page.

### Group B — Gameplay Mechanics
5. **Question type**: Which question format does this game use? Options:
   - `image_guess` — player sees an image, types an answer
   - `unscramble` — player unscrambles letter tiles
   - `multiple_choice` — player picks from 4 options
   - `emoji_guess` — player sees emoji, types an answer
   - **Other** — describe the mechanic in detail so we can design the question_type value
6. **Answer format**: What does the player type or select? (e.g. "a cricketer's full name", "a country code", "a year")
7. **Timer**: How many seconds per question? (current games: Guess=15s, Unscramble=30s)
8. **Questions per session**: How many questions in one game session? (default: 10)
9. **Scoring**: Base points per correct answer? (default: 100). Is there a speed bonus? Hint penalty?
10. **Hints**: Will players be able to request hints? If yes, describe what hints look like (text clue, reveal a letter, reveal a category, etc.)
11. **Autocomplete**: Does the answer input need autocomplete suggestions? (yes/no)

### Group C — Question Data
12. **What data does each question require?** List every field an admin needs to fill in when adding a question (e.g. for image_guess: image file, correct answer, aliases, difficulty, explanation).
13. **Where do answers come from?** (e.g. cricketer names from the cricketers table, country names, free-form text)
14. **Is the question_text field used?** If yes, what does it store? (For unscramble, it stores `COUNTRY|ROLE`. For image_guess it is null.)
15. **Are there visual assets?** (images, animations, etc.) Where are they stored?

### Group D — Admin & Content
16. **Admin tab name**: What label should the admin panel tab show for this game?
17. **What fields does the "Add Question" form need?** List them all (they become form fields in admin.tsx).
18. **What does each question look like in the admin list view?** (e.g. thumbnail + answer text + difficulty)

### Group E — Frontend
19. **Route path**: What URL should this game live at? (e.g. `/play/emoji-cricket`, following the existing `/play/guess` and `/play/unscramble` pattern)
20. **Asset thumbnail**: Does this game need a thumbnail image for the homepage/games page? (If yes, the user will provide the image file.)
21. **Any special UI elements?** (e.g. a keyboard, colour picker, drag-and-drop, etc.)

### Group F — Technical
22. **Does this game reuse the existing `cricketers` autocomplete table?** (yes/no)
23. **Does this game reuse the existing `question_sets` / `questions` / `question_options` DB tables?** (almost certainly yes — confirm)
24. **Any new DB columns needed?** (e.g. a new field on Question not currently in the schema)
25. **Is the existing fuzzy-match answer checking appropriate?** (yes/no, or describe what matching logic is needed)

---

## PHASE 1 — Plan and Confirm

Once you have all answers, present a written implementation plan to the user covering:
- New DB migration (if needed)
- Backend changes (sessions router, admin router)
- Frontend changes (new route file, game-data.ts, admin tab)
- Files to create, files to modify

Ask the user: "Does this plan look correct before I start coding?" Wait for explicit confirmation.

---

## PHASE 2 — Database

### 2a. Check if new columns are needed
If the user confirmed new DB columns are required:
1. Create a new Alembic migration:
   ```
   cd backend
   python -m alembic revision --autogenerate -m "add_<game_slug>_fields"
   ```
2. Review the generated migration file in `backend/alembic/versions/`. Edit it if needed.
3. Apply: `python -m alembic upgrade head`

If only new question data (not new columns), skip to 2b.

### 2b. Seed the game row
In `backend/app/scripts/seed.py`, add the new game entry inside the `seed_games()` function. Follow the exact same pattern as the existing games:
```python
Game(
    slug="<slug-from-user>",
    name="<name-from-user>",
    status="active",
    sort_order=<next number>,
    config={},  # add any engine config the game needs
)
```
Then add a default `QuestionSet` for this game.

Run seed: `cd backend && python -m app.scripts.seed`

---

## PHASE 3 — Backend: Sessions Router

File: `backend/app/routers/sessions.py`

### 3a. `_sanitize_question()` — add new question type
Inside `_sanitize_question()`, add an `elif` branch for the new `question_type`:
```python
elif q.question_type == "<new_type>":
    # Add all client-safe fields here
    # NEVER include the correct answer
    base["<field>"] = q.<field>
```

### 3b. Scramble / transform helper (if needed)
If the game requires server-side transformation of question data (like `_scramble()` for unscramble), add a private helper function `_<transform_name>()` above `_sanitize_question()`. Follow the same pattern: deterministic seed based on `session_id * 100 + q.id`.

### 3c. Correctness check in `submit_answer()` (if needed)
If the answer format is different from the existing normalize+fuzzy-match pipeline, add a new branch in `submit_answer()` after loading the question. The existing pipeline handles: normalize to lowercase → exact match → fuzzy SequenceMatcher. If the new game needs something else (e.g. multiple-choice option index), add it here.

---

## PHASE 4 — Backend: Admin Content Router

File: `backend/app/routers/admin_content.py`

### 4a. Add endpoint: `POST /api/admin/questions/<game_type>`
Create a new endpoint for adding questions for this game type. Follow exactly the same pattern as `add_image_guess_question` or `add_unscramble_question`:
- Use HTTP Basic Auth (`Depends(verify_admin)`)
- Accept all fields the user defined in Group C/D
- Store answers in `QuestionOption(is_correct=True)`
- Store any display-only metadata in `question_text` or `accepted_aliases`
- If assets are uploaded, call `upload_bytes()` and use `public_url()`
- Never return the correct answer in the response body

### 4b. Update `list_questions()` (if needed)
If the new question type has custom fields that should appear in the admin list view, update the response dict in `list_questions()` to include them.

---

## PHASE 5 — Backend: Games Router

File: `backend/app/routers/games.py`

No changes needed here unless the game has a custom daily-challenge rotation logic. The existing endpoints handle all game types generically.

---

## PHASE 6 — Frontend: Static Metadata

File: `frontend/src/lib/game-data.ts`

Add the new game to the `GAMES` array:
```typescript
{
  id: "<slug-from-user>",       // must match the DB slug exactly
  name: "<display-name>",
  hook: "<tagline-from-user>",
  path: "/play/<route-segment>",
}
```

---

## PHASE 7 — Frontend: Config

File: `frontend/src/lib/config.ts`

Add a constant for the round duration:
```typescript
<GAME_NAME>_ROUND_SECONDS: <seconds-from-user>,
```

---

## PHASE 8 — Frontend: API Types

File: `frontend/src/lib/api.ts`

Add any new fields to `SessionQuestion` type if the new question type sends different fields (e.g. an `emoji` field, an `options` array). Also add a new admin endpoint method in `api.admin.*` for adding questions of the new type, following the same pattern as `addImageGuessQuestion` and `addUnscrambleQuestion`.

---

## PHASE 9 — Frontend: New Game Route

Create a new file: `frontend/src/routes/play.<slug-segment>.tsx`

This file is the main game UI. Follow the **exact same phase-state-machine pattern** as `play.guess.tsx` and `play.unscramble.tsx`:

### Required phases:
- `"setup"` — set picker (reuse the `<SetPicker>` pattern; show "🎲 All sets" + named sets)
- `"loading"` — API call in progress
- `"error"` — show error + retry button
- `"playing"` — main game loop
- `"done"` — show `<ResultScreen>`

### Required anti-cheat patterns (NEVER omit):
- Store played question IDs in `sessionStorage[GAME_CONFIG.PLAYED_QIDS_KEY_PREFIX + GAME_SLUG]`
- Send `exclude_ids` in `startSession` call
- Use `useState<number>(GAME_CONFIG.<GAME>_ROUND_SECONDS)` for timer (explicit `number` type)
- Sign-in prompt: `tryPromptSignIn()` using `sessionStorage[GAME_CONFIG.SIGN_IN_PROMPTED_KEY]`
- Play again: `window.location.href = replayPath` (not `<Link>`) to force full reload

### Scaffold (copy and adapt from play.guess.tsx or play.unscramble.tsx):
Do not write this file from scratch. Open `play.guess.tsx`, copy the structure, and adapt it for the new game type. Preserve all the phase logic, sessionStorage patterns, and ResultScreen invocation.

---

## PHASE 10 — Frontend: Admin Tab

File: `frontend/src/routes/admin.tsx`

### 10a. Add the tab
In `DashboardShell`, add the new game to the tab array:
```typescript
const labels = {
  guess: "Guess the Cricketer",
  unscramble: "Unscramble",
  cricketers: "Cricketers List",
  <new_key>: "<Admin tab label from user>",
};
```

### 10b. Create a new `<NewGameTab>` component
Follow the exact pattern of `GuessTab` and `UnscrambleTab`:
- `useGameSets()` hook at the top
- Add-question form on the left with all fields the user defined
- Questions list on the right with edit (pencil) and delete (trash) buttons
- `EditNewGameQuestionForm` component for inline editing
- Use `api.admin.addNewGameQuestion()` and `api.admin.updateQuestion()` (PATCH already exists)

---

## PHASE 11 — Frontend: Thumbnail

If the user needs a thumbnail:
1. Ask for the image file if not already provided
2. Place it in `frontend/src/assets/game-<slug>.jpg` (convert to JPG if needed, target ~60KB)
3. Import and add it to the `THUMBS` map in both `index.tsx` and `games.tsx`

---

## PHASE 12 — Tests

File: `backend/tests/test_sessions.py` (and `test_admin.py`)

Add test coverage for the new game type:
- `test_start_session_<game_type>()` — start a session for the new game, verify sanitized questions don't contain answers
- `test_submit_answer_<game_type>_correct()` — correct answer returns `is_correct=True`
- `test_submit_answer_<game_type>_wrong()` — wrong answer returns `is_correct=False`
- `test_admin_add_<game_type>_question()` — admin can add a question
- `test_admin_edit_<game_type>_question()` — admin can edit a question via PATCH

Run tests and verify coverage stays above 90%:
```bash
cd backend && pytest --cov=app --cov-report=term-missing
```

---

## PHASE 13 — Verify End-to-End

1. **Start backend**: `cd backend && uvicorn app.main:app --reload`
2. **Start frontend**: `cd frontend && pnpm dev`
3. **Check homepage** (`/`): new game card appears with correct name, hook, and thumbnail
4. **Check games page** (`/games`): new game listed
5. **Check admin** (`/admin`): new tab visible, can add a question
6. **Play through the game**: start session → answer questions → complete → result screen
7. **Verify anti-cheat**: open DevTools → Network → confirm no correct answers in any API response before submission
8. **Check leaderboard** (`/leaderboard`): update the leaderboard page if it should show scores for the new game (currently hardcoded to `guess-the-cricketer`)

---

## PHASE 14 — Commit Checklist

Before committing:
- [ ] `cd frontend && npx tsc --noEmit` → zero errors
- [ ] `cd frontend && npx vite build` → clean build
- [ ] `cd backend && pytest --cov=app --cov-report=term-missing` → coverage ≥ 90%
- [ ] No hardcoded configuration values — everything in `config.ts` or `config.py`
- [ ] No correct answers anywhere in client-side code or API responses (before submission)
- [ ] No fake/mocked data
- [ ] New Alembic migration checked in (if DB schema changed)
- [ ] `backend/app/scripts/seed.py` updated with new game + default set
- [ ] PR title follows Conventional Commits: `feat: add <game-name> game`

---

## Standards Reminder

- **Anti-cheat is non-negotiable**: answers live server-side only. Every `_sanitize_question()` branch must be reviewed.
- **Config values go in config files**: no magic numbers in component code.
- **Consistent UX**: new game must use the same phase state machine, set picker, sign-in prompt, and ResultScreen as existing games.
- **Database migrations**: never `ALTER TABLE` manually. Always generate an Alembic migration.
- **TypeScript strict mode**: no `any`, no `!` non-null assertions unless absolutely necessary, explicit types on all `useState` calls that use const literals.
