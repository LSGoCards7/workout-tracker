# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IRON LOG — a dumbbell hypertrophy workout tracking PWA. The core application is a single HTML file (`iron_log.html`) with inline CSS and JavaScript. Cloud sync via Cloudflare Workers + KV. No frameworks, no SDK — just native `fetch()` and service worker.

## Development

- **Run locally**: Open `iron_log.html` directly in a browser (file:// — sync disabled, shows info banner)
- **Run hosted**: Deploy to GitHub Pages for full PWA + sync support
- **Worker dev**: `cd worker && wrangler dev` for local sync testing, `wrangler deploy` to push
- **No build/lint/test commands** — there is no package.json, no bundler, no test framework
- **App changes** go in `iron_log.html`; sync backend changes go in `worker/src/index.js`

## Architecture

### File structure
| File | Purpose |
|------|---------|
| `iron_log.html` | The entire app — CSS, HTML, JS inline (~1880 lines) |
| `sw.js` | Service worker — cache-first for app shell, skip sync URLs |
| `manifest.json` | PWA metadata — name, icons, theme, display mode |
| `icons/` | PWA icons (192, 512 PNG + apple-touch-icon 180) |
| `worker/src/index.js` | Cloudflare Worker — GET/PUT /sync endpoints with KV storage |
| `worker/wrangler.toml` | Worker config — KV namespace binding |

### HTML structure (`iron_log.html`)
Organized in order: FOUC `<script>` → `<style>` → `<div id="file-banner">` → `<div id="app">` → `<div id="rest-timer">` → `<div id="difficulty-prompt">` → `<div id="toast">` → `<script>`.

### State machine rendering
- Global `state` object tracks current view, selected workout, active exercise, etc.
- `render()` function reads `state` and rebuilds `#app` innerHTML
- Navigation between views: update `state.view` then call `render()`
- Views: `home`, `workout`, `history`, `progress`, `settings`
- `renderTimer()` updates `#rest-timer` independently (fixed overlay, outside `#app`)

### Chart utility
- `renderLineChart(dataPoints, options)` — returns SVG markup string, compatible with `render()` innerHTML pattern
- `dataPoints`: `[{label: string, value: number}]` — label is typically `"YYYY-MM-DD"`
- `options`: `{width, height, color, yLabel, xLabelFn, emptyMsg, yFormat, secondaryData, secondaryColor}`
- Uses CSS variables (`--accent`, `--border-subtle`, `--text-dim`, `--bg-surface`) — adapts to dark/light theme automatically
- LTTB downsampling when >50 points, handles edge cases (0 points, 1 point, flat data, NaN values)
- `<title>` tooltips on data points (desktop hover only; no touch support yet)
- Used by Exercise Progression Charts in Progress view (weight + volume over time per exercise)

### Volume & progression utilities
- `calcExVolume(exercise)` — sum of `reps * weight` for completed sets only. Returns 0 if no sets or weight is 0.
- `calcSessionVolume(exerciseData)` — sum of all exercise volumes in a session. Skips `__meta` key.
- `isReadyToProgress(exIndex)` — returns true if all sets completed AND all reps >= `repsHigh`. Used by overload badge in workout view.
- Progressive overload badge: shown below notes input when `isReadyToProgress()` is true. Suggests +5 lbs or harder technique at max weight (50 lbs).

### Session duration
- `state.workoutStartTime` tracks when workout started (epoch ms)
- `startWorkout()` sets start time (fresh `Date.now()` or restored from `__meta.startTime` for crash recovery)
- `completeSet()` persists `__meta.startTime` to history for crash resilience
- `finishWorkout()` saves data (crash resilience), then shows difficulty prompt overlay
- `setDifficulty(rating)` computes `__meta.duration` (seconds), saves `__meta.difficulty`, deletes `__meta.startTime`, goes home
- `loadData()` cleans up orphaned `startTime` entries (crash without finish)
- Duration displayed in History view card headers (e.g., "Lower A — Quad Focus · 47 min")

### Rest timer auto-start
- **localStorage key**: `ironlog-autorest` — `'false'` to disable, absent/any other value = enabled (default ON)
- `completeSet()` conditionally calls `startRest()` based on setting. Skips last set of last exercise.
- Settings toggle in Settings → Workout section

### Training frequency heatmap
- `renderHeatmap()` — returns SVG markup string, 7×12 grid (Mon-Sun × 12 weeks)
- Placed at top of Progress view, before exercise progress blocks
- Uses `hasCompletedSets()` to determine workout days (consistent with Home view)
- Empty state: dim grid + "Start working out to fill your heatmap" message
- CSS: `.heatmap-container` centered, responsive SVG viewBox

### Personal records board
- `computePRs(dayName, exIndex)` — scans `state.history`, returns `{weightPR, repPR, volumePR}` each `{value, date}` or null
- `checkAndToastPRs(exIndex)` — called in `completeSet()` wrapped in try-catch. Compares current workout against historical bests (excluding today). Toasts if strictly exceeding previous best.
- `state.prToastedThisSession` — Set of strings like `"weight-0"` to prevent duplicate toasts. Reset in `startWorkout()`.
- PR toast priority: weight > volume > rep. Skips weight=0 exercises and first-ever sessions.
- PR badges shown in Progress view under each exercise (gold/amber pills).

### Exercise progression charts
- `state.expandedChart` — holds `"DayName-ExIndex"` key or null. Only one chart open at a time.
- Exercise names in Progress view are clickable — toggle expand/collapse with `▸`/`▾` indicators.
- Expanded: shows weight-over-time and volume-over-time line charts using `renderLineChart()`.
- Desktop responsive: `.progress-ex-row.expanded` spans full width (overrides 50% inline-block).

### Workout difficulty rating
- **UX flow**: Finish Workout → data saved → difficulty overlay → rating or skip → duration computed → go home
- `showDifficultyPrompt()` — renders 1-10 color-coded buttons + Skip into `#difficulty-prompt` div (z-index 175, between rest-timer 150 and toast 200)
- `setDifficulty(rating)` — saves `__meta.difficulty` (1-10 or null for skip), computes duration, clears overlay, goes home
- Double-tap guard: `finishWorkout()` returns early if overlay already showing
- Backdrop click = skip (escape hatch)
- History view shows color-coded RPE pip (green 1-3, yellow 4-6, red 7-10) next to duration
- CSS: `.difficulty-card`, `.difficulty-btn` (HSL gradient green→red), `.rpe-pip` with color variants

### Data persistence
- **Primary**: LocalStorage under key `ironlog-data`
- **Backup**: IndexedDB (`ironlog-backup` database) — fire-and-forget write on every save, fallback read if localStorage empty
- **Cloud**: Cloudflare KV via Worker — debounced 5s sync after saves, pull on startup
- **Sync settings**: Separate localStorage key `ironlog-sync` — `{ syncKey, syncEnabled, lastSyncedAt }`
- v2 format: `{ version: 2, history, checklist, lastExportDate, backupDismissDate }`
- Auto-migration from v1 (no version field) with safety backup to `ironlog-data-v1-backup`
- `saveData()` writes localStorage + IndexedDB + triggers debounced cloud sync
- Export/import JSON with merge vs replace flow
- Data shape:
  - `history["YYYY-MM-DD"]["Day Name"][exerciseIndex]` → `{ weight, technique, sets: [{reps, completed}], notes }`
  - `history["YYYY-MM-DD"]["__meta"]` → `{ startTime?, duration?, difficulty? }` — session metadata. `startTime` is ephemeral (deleted on finish), `duration` is permanent (seconds), `difficulty` is 1-10 or absent. Reserved key — all history iteration must filter it.
  - `checklist["YYYY-Www"][itemIndex]` → completed item indices

### Cloud sync architecture
- **Worker URL**: Set in `SYNC_WORKER_URL` constant at top of `<script>` (empty = sync disabled)
- **Auth**: Passphrase-based. Client sends raw passphrase as query param; Worker hashes with SHA-256 as KV key
- **Endpoints**: `GET /sync?key=X` (pull), `PUT /sync?key=X` (push), `GET /sync/previous?key=X` (rollback)
- **KV stores**: `current` (latest data + serverUpdatedAt) and `previous` (safety net before each write)
- **Conflict resolution**: Timestamp comparison. If cloud newer → auto-pull. First sync with data on both sides → user prompt
- **Debounce**: 5s after last `saveData()`. Max one sync per 5s window
- **Offline**: Sets `needsSync=true`, syncs on `online` event

### Service worker (`sw.js`)
- **Cache name**: `ironlog-cache-v3` (bump version to force update)
- **Strategy**: Cache-first for app shell + fonts. Network-first for sync URLs (never cached)
- **Activation**: `skipWaiting()` + `clients.claim()` for immediate takeover
- **Update**: "Check for Updates" button in Settings calls `registration.update()`
- **Escape hatch**: Unregister via devtools → Application → Service Workers → Unregister

### Program structure
- 4-day upper/lower dumbbell split: Upper 1, Lower 1, Upper 2, Lower 2
- Weekly schedule: Sat/Sun/Tue/Thu workout days, Mon/Wed/Fri rest
- Exercises defined in `PROGRAM` object with name, sets, rep range, default weight, tempo, rest time
- Techniques: standard, 1.5 reps, pause reps, rest-pause, mech. drop set, slow tempo

### Theming
- **CSS custom properties**: All colors defined as variables in `[data-theme="dark"]` and `[data-theme="light"]` blocks
- **Theme attribute**: `data-theme="dark|light"` on `<html>` element controls active theme
- **Preference storage**: `localStorage.getItem('ironlog-theme')` → `'system'` (default), `'dark'`, or `'light'`
- **FOUC prevention**: Inline `<script>` in `<head>` reads preference and sets `data-theme` before CSS parses
- **System tracking**: `matchMedia('prefers-color-scheme: dark')` change listener updates when in `system` mode
- **Cross-tab sync**: `storage` event listener syncs theme preference across browser tabs
- **Meta theme-color**: Dynamically updated by `applyTheme()` (`#0f172a` dark, `#f1f5f9` light)
- **`color-scheme` CSS property**: Set on both theme blocks so native browser elements (scrollbars, selects) adapt
- **Settings toggle**: 3-way (Auto/Dark/Light) in Settings → Appearance section
- To add a new themed color: add a variable in both `[data-theme]` blocks, then use `var(--name)` in CSS

### Styling
- Dark theme: background `#0f172a`, text `#e2e8f0`, accent `#4ade80`
- Light theme: background `#f1f5f9`, text `#1e293b`, accent `#16a34a`
- JetBrains Mono font throughout
- Mobile-first, max-width 480px, fixed bottom nav bar
- Responsive breakpoints: 768px (tablet, 720px max), 1200px (desktop, 1000px max)
- iOS PWA meta tags for home screen installation
- Toast notifications: `#toast` div (fixed, outside `#app`, slide-in animation)
- File protocol banner: `#file-banner` shows warning when opened via `file://`

## Session Continuity

At the start of every session:
1. Check for the most recent HANDOVER-*.md file in `handovers/`
2. If one exists, read it completely before doing anything else
3. Acknowledge what was accomplished in the previous session and confirm the next steps
4. If the handover references unresolved bugs or failing tests, verify their current status before moving forward

Do NOT read all HANDOVER-*.md files at startup — only the most recent one. Older handover files exist as historical reference and should only be consulted if:
- The current handover references a decision or issue from a prior session
- The user asks about something from an earlier session
- Context about an architectural decision needs to be traced back

If no HANDOVER-*.md exists, ask the user for context about what to work on.

## Development Approach

This project is built using Claude Code as the primary development tool. The founder directs Claude Code rather than writing code manually. Follow these principles:

### General

- Be explicit and specific. When implementing features, go beyond the basics to create fully-featured, production-grade code.
- Default to implementing changes rather than only suggesting them. If intent is unclear, infer the most useful action and proceed.
- After completing tool use or a task, provide a quick summary of the work done.
- Investigate and read relevant files before answering questions about the codebase. Never speculate about code you haven't opened.
- Avoid over-engineering. Only make changes directly requested or clearly necessary. Don't add features, abstractions, or defensive coding beyond what's needed for the current task.

### Code Quality

- Write high-quality, general-purpose solutions. Do not hard-code values or create solutions that only work for specific test inputs.
- Keep solutions simple and focused. A bug fix doesn't need surrounding code cleaned up. A simple feature doesn't need extra configurability.
- Don't add docstrings, comments, or type annotations to code you didn't change. Only add comments where the logic isn't self-evident.
- If a task is unreasonable, infeasible, or if tests are incorrect, inform the user rather than working around them.

### State Management & Long Tasks

- Use git for state tracking. Commit frequently with descriptive messages.
- For long tasks, plan work clearly and spend the full output context working systematically. Don't stop early.
- Track progress in `progress.txt` and test status in `tests.json` when working across multiple sessions.
- If context is running low, save current progress and state before the context window refreshes.
- Create and maintain test suites. Never remove or edit existing tests — this could lead to missing or buggy functionality.

### File Management

- If you create temporary files, scripts, or helpers for iteration, clean them up at the end of the task.
- Minimize net new file creation unless the files are part of the deliverable.

### Parallel Execution

- If calling multiple tools with no dependencies between them, make all independent calls in parallel.
- Never use placeholders or guess missing parameters in tool calls.

---

## Workflow Orchestration

### 1. Plan Mode Default

- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately — don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy

- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop

- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done

- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)

- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing

- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

---

## Task Management

1. **Plan First:** Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan:** Check in before starting implementation
3. **Track Progress:** Mark items complete as you go
4. **Explain Changes:** High-level summary at each step
5. **Document Results:** Add review section to `tasks/todo.md`
6. **Capture Lessons:** Update `tasks/lessons.md` after corrections

---

## Core Principles

- **Simplicity First:** Make every change as simple as possible. Impact minimal code.
- **No Laziness:** Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact:** Changes should only touch what's necessary. Avoid introducing bugs.
