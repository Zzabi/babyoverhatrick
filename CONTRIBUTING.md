# Contributing to BabyOverHattrick

Thank you for your interest in contributing to BabyOverHattrick. This is an open project and contributions of all kinds are welcome — whether you are fixing a bug, improving documentation, adding cricket questions through the admin panel, or proposing a new game type.

---

## Table of Contents

1. [Types of Contributions Welcome](#1-types-of-contributions-welcome)
2. [Development Setup](#2-development-setup)
3. [Branching Strategy](#3-branching-strategy)
4. [Code Standards](#4-code-standards)
5. [Testing](#5-testing)
6. [Pull Request Process](#6-pull-request-process)
7. [Reporting Issues](#7-reporting-issues)
8. [GitHub Configuration (Repo Owner)](#8-github-configuration-repo-owner)
9. [Content Contributions](#9-content-contributions)
10. [License](#10-license)

---

## 1. Types of Contributions Welcome

- **Bug fixes** — anything broken, incorrect, or producing unexpected results
- **New content** — adding cricketers and questions via the admin panel (no code changes required; see [Content Contributions](#9-content-contributions))
- **New game types** — Phase 1 has two games; new game proposals and implementations are welcome
- **Documentation improvements** — clearer explanations, fixing inaccuracies, adding examples
- **Performance improvements** — measurable, with benchmarks
- **Accessibility improvements** — the frontend targets broad usability
- **Test coverage** — additional tests for existing untested paths

---

## 2. Development Setup

Follow [SETUP.md](./SETUP.md) for the full local development walkthrough.

Key point for local development: set `DEV_BYPASS_AUTH=true` in your `.env` file to skip Clerk JWT validation. This means you do not need a Clerk account or real tokens when working on the backend locally. The frontend still loads Clerk; you can sign in or work in guest mode.

```bash
# .env (local dev)
DEV_BYPASS_AUTH=true
```

---

## 3. Branching Strategy

- `main` is the protected default branch. Direct pushes are not allowed.
- All work happens on feature or fix branches, opened as pull requests against `main`.

| Branch type | Naming convention | Example |
|---|---|---|
| New feature | `feature/your-feature` | `feature/streak-endpoint` |
| Bug fix | `fix/your-fix` | `fix/hint-timer-reset` |
| Documentation | `docs/your-change` | `docs/setup-clarification` |
| Tests | `test/your-addition` | `test/session-submit-edge-cases` |
| Chores / tooling | `chore/your-change` | `chore/update-dependencies` |

---

## 4. Code Standards

### Python (backend)

- Follow [PEP 8](https://peps.python.org/pep-0008/).
- **Type hints are required on every function signature** — parameters and return types. No bare `dict` or untyped returns.
- Public functions and classes must have at least a one-line docstring.
- **No hardcoded secrets or credentials.** All configuration goes through `backend/app/core/config.py` as a typed `pydantic-settings` field, with a corresponding entry in `.env.example`.
- New database columns or tables require an Alembic migration:
  ```bash
  cd backend
  python -m alembic revision --autogenerate -m "describe your change"
  python -m alembic upgrade head
  ```
  Never alter live table schemas manually or via raw SQL in migrations without also updating the ORM model.
- New API endpoints belong in the appropriate router file under `backend/app/routers/`. Register the router in `app/main.py` with its prefix.
- Use the `get_current_user` dependency from `app/auth/` for player-facing endpoints. Use the `require_admin` dependency for admin endpoints. Do not write inline auth checks.

### TypeScript (frontend)

- TypeScript strict mode is enabled. **No `any`.** If you are reaching for `any`, define a proper type.
- All API calls go through `frontend/src/lib/api.ts`. Do not use `fetch` or `axios` directly in components.
- Define TypeScript types for new API responses in `api.ts` alongside the functions that return them.
- New configuration constants (timer durations, display strings, etc.) belong in `frontend/src/lib/config.ts`.
- New pages are new files in `frontend/src/routes/`. TanStack Router picks them up automatically and regenerates `routeTree.gen.ts`. **Do not edit `routeTree.gen.ts` manually** — it is auto-generated and your changes will be overwritten.
- Follow existing component patterns. Use shadcn/ui for new UI primitives. Style with Tailwind utility classes.

### Anti-cheat principle (applies to all code)

**Answers must never be sent to the client before the client submits an answer.** This is a core architectural invariant. Review every new endpoint, query, and serializer against this rule before opening a PR. Violating it cannot be fixed with a minor patch — it requires invalidating cached client state.

---

## 5. Testing

### Running the test suite

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

### Requirements

- **Coverage must remain above 90%.** A PR that drops coverage below this threshold will not be merged.
- **Every new backend endpoint must have tests.** At minimum: happy path, authentication failure, and at least one invalid input case.
- Test files live in `backend/tests/`. Mirror the module structure: tests for `app/routers/sessions.py` go in `backend/tests/routers/test_sessions.py`.
- Use pytest fixtures for database setup and teardown. Do not write to the production or development database in tests.

---

## 6. Pull Request Process

### PR title format

Use [Conventional Commits](https://www.conventionalcommits.org/) style:

| Prefix | When to use |
|---|---|
| `feat:` | A new feature or capability |
| `fix:` | A bug fix |
| `docs:` | Documentation changes only |
| `test:` | Adding or correcting tests |
| `chore:` | Tooling, dependency updates, CI |
| `refactor:` | Code restructuring without behaviour change |

Example: `feat: add streaks endpoint with daily reset`

### Before opening a PR

1. Your branch is up to date with `main`.
2. All tests pass locally: `cd backend && pytest --cov=app --cov-report=term-missing`.
3. Coverage has not dropped below 90%.
4. You have filled in the PR template (`.github/pull_request_template.md`).
5. If you added a new environment variable, it is documented in `.env.example` and in `CLAUDE.md`.

### Review

- One reviewer approval is required before merging.
- Status checks (tests) must pass.
- Address all review comments before requesting re-review.
- The reviewer may request changes; this is normal and not a rejection.

---

## 7. Reporting Issues

### Bug reports

Please include:

- **Steps to reproduce** — the exact sequence of actions that triggers the bug
- **Expected behaviour** — what should have happened
- **Actual behaviour** — what happened instead
- **Environment** — browser and version (for frontend bugs), OS, Python/Node version (for local setup bugs)
- **Screenshots or error messages** if applicable

Open a bug report at the [GitHub Issues page](https://github.com/zzabi/babyoverhatrick/issues/new?template=bug_report.yml).

### Feature requests

Describe the **use case** — why does this matter to a cricket trivia player? — before describing the feature itself. A clear use case helps evaluate priority and design.

Open a feature request at the [GitHub Issues page](https://github.com/zzabi/babyoverhatrick/issues/new?template=feature_request.yml).

---

## 8. GitHub Configuration (Repo Owner)

This section is for **Mohammed / zzabi** and documents how to configure the repository's GitHub settings to match the contribution workflow described above.

### Branch protection on `main`

Go to **Settings → Branches → Add rule**, set the branch name pattern to `main`, and enable:

- Require a pull request before merging
- Require approvals: **1**
- Require status checks to pass before merging (add the test workflow once CI is set up)
- Do not allow bypassing the above settings

### Issue templates

Create the following files. GitHub picks them up automatically.

**`.github/ISSUE_TEMPLATE/bug_report.yml`**

```yaml
name: Bug Report
description: Report a bug or unexpected behaviour
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to fill out this bug report.
  - type: textarea
    id: steps
    attributes:
      label: Steps to reproduce
      description: The exact sequence of actions that triggers the bug.
      placeholder: |
        1. Go to /play/guess
        2. Start a session
        3. ...
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected behaviour
      description: What should have happened?
    validations:
      required: true
  - type: textarea
    id: actual
    attributes:
      label: Actual behaviour
      description: What happened instead?
    validations:
      required: true
  - type: textarea
    id: environment
    attributes:
      label: Environment
      description: Browser/version, OS, Python/Node version if relevant.
      placeholder: |
        Browser: Chrome 125
        OS: macOS 14
    validations:
      required: false
  - type: textarea
    id: extras
    attributes:
      label: Screenshots or error messages
      description: Paste any relevant error output or attach screenshots.
    validations:
      required: false
```

**`.github/ISSUE_TEMPLATE/feature_request.yml`**

```yaml
name: Feature Request
description: Suggest a new feature or improvement
labels: ["enhancement"]
body:
  - type: markdown
    attributes:
      value: |
        Describe the use case before the feature — this helps with prioritisation and design.
  - type: textarea
    id: use_case
    attributes:
      label: Use case
      description: Why does this matter? Who benefits and how?
    validations:
      required: true
  - type: textarea
    id: feature
    attributes:
      label: Proposed feature
      description: Describe the feature you would like to see.
    validations:
      required: true
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives considered
      description: Have you considered any workarounds or alternative approaches?
    validations:
      required: false
```

### PR template

**`.github/pull_request_template.md`**

```markdown
## Summary

<!-- What does this PR do? One or two sentences. -->

## Type of change

- [ ] Bug fix (`fix:`)
- [ ] New feature (`feat:`)
- [ ] Documentation update (`docs:`)
- [ ] Test addition or correction (`test:`)
- [ ] Chore / tooling (`chore:`)
- [ ] Refactor (`refactor:`)

## Changes

<!-- Bullet list of what changed. -->

-

## Testing

- [ ] Backend tests pass: `cd backend && pytest --cov=app --cov-report=term-missing`
- [ ] Coverage is at or above 90%
- [ ] New endpoints have tests (happy path, auth failure, invalid input)

## Anti-cheat check

- [ ] No answer values are sent to the client before the client submits an answer

## Environment variables

- [ ] No new env vars introduced, OR new vars are documented in `.env.example` and `CLAUDE.md`

## Screenshots (if UI change)

<!-- Attach before/after screenshots for any visible UI change. -->

## Notes for reviewer

<!-- Anything the reviewer should know about the approach or trade-offs. -->
```

### CODEOWNERS

Create **`.github/CODEOWNERS`** to auto-assign review to the project owner for all changes:

```
# Global owner — review required on every PR
* @zzabi
```

You can make this more granular as the team grows:

```
# Backend
/backend/ @zzabi

# Frontend
/frontend/ @zzabi

# Infrastructure and docs
/docker-compose.yml @zzabi
/docs/ @zzabi
```

---

## 9. Content Contributions

The fastest way to improve the game is to add more cricketers and questions. You do not need to write any code to do this.

1. Access the admin panel at `/admin` (credentials from the project owner).
2. Use the **Cricketers** section to add a new cricketer: name, country, playing role, and upload a photo. The photo is stored in object storage; the filename is randomised automatically.
3. Use the **Questions** section to add questions for each game type:
   - For **Guess the Cricketer**: select the cricketer and the image to display.
   - For **Unscramble the Name**: select the cricketer and optionally add hint text (shown as the third hint tier after country and role).
4. Assign questions to a question set so they appear in rotation.

If you want to contribute a batch of questions but do not have admin credentials, open a GitHub issue with the cricketer names and any supporting details, and a maintainer will add them.

---

## 10. License

By contributing to this repository, you agree that your contributions will be licensed under the [MIT License](./LICENSE) that covers this project.
