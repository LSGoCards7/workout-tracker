# Iron Log — Feature Roadmap

*Generated 2026-02-14. User: 33M, home gym, 10-50 lb dumbbells, body recomp goal, desktop-primary (2560x1440).*

**Critical file:** `iron_log.html` (~1379 lines). All changes go here unless noted.

---

## Architectural Decisions (all tiers)

**SVG over Canvas for Charts** — `render()` (line 1272) rebuilds the full DOM on every state change. Canvas requires post-insertion JS drawing and would be destroyed each time. SVG generates as markup strings, compatible with the existing rendering pattern.

**Derived State for PRs** — Compute from history on demand via `computePRs(dayName, exIndex)`. No separate storage = no sync/consistency bugs.

**Session Metadata via `__meta` Key** — Duration and difficulty stored in `state.history[date]["__meta"]`. Reserved key alongside day names. Avoids changing the per-exercise array structure that 12+ functions depend on.

**Data Migration v2 to v3** — Same pattern as v1-to-v2 (lines 537-544): backup raw v2 string, then transform. New top-level fields: `bodyWeight`, `measurements`, `nutrition`. `__meta` added on-demand.

**Nav Bar** — Currently 2 items, `gap: 48px` (line 211). Tier 2 adds "Body" as 3rd. Reduce gap to 32px/48px/80px (mobile/tablet/desktop). Cap at 4 items.

---

## Tier 1: Progress & Analytics Overhaul

### Build Order

```
Phase A (no dependencies, build in any order):
  1. SVG Chart Utility              [DONE] 3943d3c
  2. Volume Load Tracking           [DONE] c51a034
  3. Session Duration Timer         [DONE] cbed3ee
  4. Rest Timer Auto-Start          [DONE] 350c8e8
  5. Progressive Overload Advisor   [DONE] 3cfd5e4

Phase B (depends on Phase A):
  6. Exercise Progression Charts    [DONE] 5650c31
  7. Workout Difficulty Rating       [DONE] 97fa1d6
  8. Personal Records Board          [DONE] 95f6e02
  9. Training Frequency Heatmap      [DONE] 94f5127
```

---

### 1. SVG Chart Utility [Small]

**New function:** `renderLineChart(dataPoints, options)` returning SVG markup string.

**Inputs:** Array of `{label, value}`, options: `{width, height, color, yLabel, xLabelFn, emptyMsg}`.

**Features:**
- SVG viewBox for responsive scaling (no fixed pixel sizes)
- Polyline for data line, circles for data points
- Y-axis: auto-scale `min-10%` to `max+10%`, 3-4 horizontal grid lines
- X-axis: first, last, and ~3 evenly-spaced date labels
- Native tooltips via `<title>` on circle elements (no JS events)
- LTTB (Largest-Triangle-Three-Buckets) sampling when >50 points
- Returns empty-state div when 0 points
- Theme-compatible: uses CSS variable colors

**Edge cases:** 0 pts = empty msg, 1 pt = dot only, all same value = flat line, values at 0 = clamp y-min to 0.

---

### 2. Volume Load Tracking [Small]

**New functions:**
- `calcExVolume(exercise)` — sum of `(reps * weight)` for completed sets only
- `calcSessionVolume(exerciseArray)` — sum of all exercise volumes

**Modifications:**
- `renderHistory()` (lines 1095-1112): append per-exercise volume and session total
- `getProgressData()` (lines 779-786): add `volume` field to returned entries

**No data migration.** Pure computation from existing data. Cache results in `state` to avoid re-computation.

**Edge cases:** 0 completed sets = 0 volume. Weight = 0 (guard with `|| 0`).

---

### 3. Session Duration Timer [Small]

**Modifications:**

- `startWorkout()` (line 614): add `state.workoutStartTime = Date.now()`. If resuming existing session, restore from `__meta.startTime`.
- `completeSet()` (line 636): after saving to history (line 641), write `__meta.startTime` if not already set.
- `finishWorkout()` (line 628): compute `duration = Math.round((now - startTime) / 1000)`, store in `__meta.duration`, delete `__meta.startTime`.
- `renderHistory()`: show formatted duration (`"47 min"`) per session.
- `loadData()`: cleanup orphaned `startTime` (crash recovery — if startTime exists but no duration, delete it).

**Edge cases:** Old sessions have no `__meta` = don't show duration. Crash before finish = orphaned startTime cleaned on load.

---

### 4. Rest Timer Auto-Start [Small]

**New localStorage key:** `ironlog-autorest` (default: `"true"`)

**Modifications:**
- `completeSet()` (line 643): wrap `startRest(restTime)` in auto-rest check. Skip if `ironlog-autorest === 'false'`. Skip if last set of last exercise.
- `renderSettings()`: add toggle in new "Workout" section (same button pattern as theme toggle, lines 1256-1260).

**Edge cases:** Rapid taps = safe (startRest already clears previous interval at line 668).

---

### 5. Progressive Overload Advisor [Small]

**New function:** `isReadyToProgress(exIndex)` — returns true if all sets completed AND all reps >= `repsHigh`.

**Modifications:**
- `renderWorkout()`: when `isReadyToProgress(i)` is true, show green badge: "Hit {repsHigh} on all sets — try {weight+5} lbs next time"
- If weight >= equipment max (50 lbs), change message: "At max weight — try a harder technique"
- Only show after ALL sets for that exercise are done.

**CSS:** `.overload-badge` — `color: var(--accent)`, small font.

**Edge cases:** `repsHigh` = 0 or undefined = skip. Equipment ceiling = different message.

---

### 6. Exercise Progression Charts [Medium]

**Modifications to `renderProgress()` (lines 1123-1159):**
- Each exercise card becomes expandable. Default: collapsed (text summary as now).
- Tap exercise name toggles `state.expandedChart` (`"Lower A-0"` or null).
- Expanded: two SVG charts below summary — weight over time + volume over time.
- Uses `renderLineChart()` with data from `getProgressData()`.
- Single-expand: opening one collapses others.

**State:** `state.expandedChart = null`

**CSS:** `.progress-chart-container` collapsible section, animated max-height. Desktop: larger chart width in 2-column grid.

**Edge cases:** 0 sessions = "No data yet". 1 session = single dot. 50+ = LTTB sampling.

---

### 7. Workout Difficulty Rating [Medium]

**UX flow:**
1. User taps "Finish Workout"
2. Rating overlay appears (rendered into new `<div id="difficulty-prompt">` outside `#app`)
3. 10 buttons (1-10) with green-to-red color gradient + "Skip" option
4. Selection saves to `__meta.difficulty`, then completes the finish flow

**New HTML element:** `<div id="difficulty-prompt"></div>` (after `#rest-timer`, before `#toast`)

**New functions:**
- `showDifficultyPrompt()` — renders rating UI into `#difficulty-prompt`
- `setDifficulty(rating)` — stores rating (1-10 or null for skip), clears prompt, calls `finishWorkoutFinal()`

**Modifications:**
- Rename current `finishWorkout()` logic to `finishWorkoutFinal()`
- New `finishWorkout()`: save data for crash resilience, then show difficulty prompt
- `renderProgress()`: add "Difficulty" section with SVG chart of difficulty over time, filterable by workout day

**State:** `state.difficultyFilter = 'all'`

**CSS:** `#difficulty-prompt` fixed overlay, z-index 175 (between timer 150 and toast 200), semi-transparent backdrop.

**Edge cases:** Skip = `null` difficulty, gaps in chart. Old sessions = no difficulty, same gap. Crash during prompt = data already saved, just missing difficulty.

---

### 8. Personal Records Board [Medium]

**New function:** `computePRs(dayName, exIndex)` — scans history, returns `{weightPR, repPR, volumePR}` each with `{value, date}`.
- Weight PR: highest weight with at least 1 completed set
- Rep PR: highest reps in any single completed set (any weight)
- Volume PR: highest single-session exercise volume

**PR detection in `completeSet()` (line 636):**
- After saving, compute PRs for current exercise
- Compare against PRs excluding current session
- If new PR: `showToast('New weight PR!', 'success')`
- Track toasted PRs in `state.prToastedThisSession = new Set()` (prevent duplicate toasts)

**Modifications to `renderProgress()`:**
- PR badges per exercise: weight PR, rep PR, volume PR with dates on hover.

**CSS:** `.pr-badge` inline pill, gold accent border.

**Edge cases:** First session = all PRs, no toast. Tie = not a new PR. Rep PR is per-set max, not total.

---

### 9. Training Frequency Heatmap [Medium]

**New function:** `renderHeatmap()` — SVG grid, 7 rows (days) x 12 columns (weeks).

**Implementation:**
- Walk back 84 days from today
- Each cell: `<rect>` colored by whether a workout was logged that day
- Month labels along top, day abbreviations along left
- Place at top of Progress view

**CSS:** `.heatmap-container` centered, responsive width. Cell colors via CSS vars.

**Edge cases:** No history = empty grid + "Start working out to fill your heatmap". `__meta`-only days don't count. Future dates not rendered.

---

## Tier 2: Body Composition Hub

### Build Order

```
Phase A (foundation):
  10. Body View Shell + Nav Bar Update
  11. Body Weight Log

Phase B (extends Body view):
  12. Body Measurements Log
  13. Simple Nutrition Log

Phase C (derived):
  14. Estimated Body Fat Calculator (needs #12)
```

### Data Migration for Tier 2

**v3 `saveData()` payload** (modify line 581):
```
version: 3, history, checklist, lastExportDate, backupDismissDate,
bodyWeight: state.bodyWeight || [],
measurements: state.measurements || [],
nutrition: state.nutrition || {}
```

**Migration in `loadData()`:** If `version === 2`, backup to `ironlog-data-v2-backup`, set `version = 3`, add empty `bodyWeight`, `measurements`, `nutrition`.

---

### 10. Body View Shell + Nav Bar [Small]

**New view:** `body` added to render() switch statement.

**Extract `renderNavBar()` function** — replaces 3 inline nav blocks (Home, History, Progress views). 3 items: History, Body, Progress. Active state highlighting via `.nav-btn.active` class.

**CSS updates:** `.nav-bar` gap reduced: 32px base, 48px at 768px, 80px at 1200px. `.nav-btn.active { color: var(--accent); }`

**`renderBody()` structure:**
- Header with title + settings gear
- Body weight section
- Measurements section
- Nutrition section
- Nav bar

---

### 11. Body Weight Log [Medium]

**Data:** `state.bodyWeight = [{date: "YYYY-MM-DD", weight: 178.5}]` sorted by date.

**New functions:**
- `addBodyWeight(weight)` — validate (50-500 lbs, parseFloat), overwrite same-day, sort, save
- `calcRollingAvg(entries, window)` — 7-day rolling average for chart overlay

**Rendering:**
- Input form: number input (step=0.1) + "Log" button, pre-filled with today's value if exists
- SVG chart: raw weights as dots + 7-day rolling average as thicker line (extend chart utility for dual-series)
- Last 10 entries list: date + weight + delta from previous
- Stats line: current, lowest, highest, trend

**Extend `renderLineChart`** to accept optional `secondaryData` for overlay line (rolling average).

**Edge cases:** No entries = input only + "Log your first weigh-in". 1 entry = dot, no average. Decimal weights allowed (step=0.1). Same-day = overwrite + toast "Updated today's weight". Value > 500 or < 50 = validation error.

---

### 12. Body Measurements Log [Medium]

**Data:** `state.measurements = [{date, values: {neck, chest, armL, armR, waist, hips, thighL, thighR}, estimatedBF}]`

**New function:** `saveMeasurements(values)` — validate, overwrite same-day, sort, save.

**Rendering:**
- "Last measured X days ago" status (or "Never measured")
- "Add Measurements" button toggles inline form (`state.showMeasurementForm`)
- Form: labeled number inputs, 2 columns on mobile, 3 on desktop, pre-filled with previous values
- Display: latest vs previous + delta from baseline (first entry)
- Delta coloring: waist/hips down = green (fat loss), arms/chest/thighs up = green (muscle gain)

**Edge cases:** Only neck + waist required (for BF calc). Missing fields = skip delta. First entry = show "baseline" instead of delta. >30 days since last = reminder prompt.

---

### 13. Simple Nutrition Log [Medium]

**Data:** `state.nutrition = {"YYYY-MM-DD": {calories: 2450, protein: 162}}`

**New functions:**
- `logNutrition(calories, protein)` — parseInt, allow partial (just one value), save
- `getWeeklyAdherence()` — count days logged + days hitting targets this week

**Rendering:**
- Two number inputs (Calories, Protein g) + "Log" button, pre-filled if today logged
- Target bars: color-coded comparison (green = on target, yellow = close, red = off)
  - Calories target: 2500 (green if 2200-2800)
  - Protein target: 150g (green if >= 150)
- Weekly adherence: "5/7 days logged, 4/7 hit protein"
- Targets stored in `localStorage('ironlog-nutrition-targets')`, configurable in Settings

**Settings addition:** Nutrition targets (calories + protein) in "Workout" section.

**Edge cases:** Log only one value = other shows "—". Value of 0 treated as null. Targets configurable.

---

### 14. Estimated Body Fat Calculator [Small]

**Navy Method (male):** `BF% = 86.010 * log10(waist - neck) - 70.041 * log10(height) + 36.76`

**Height:** Stored in `localStorage('ironlog-height')` (inches). First-time prompt in Body view if not set.

**New function:** `estimateBodyFat(neck, waist, heightInches)` — returns BF% rounded to 1 decimal.

**Rendering:**
- Auto-calculate when measurements have neck + waist
- Display: "Est. BF: 22.1% | Lean: 138.7 lbs | Fat: 39.3 lbs"
- BF% trend chart (SVG) if 2+ measurements
- Caveat: "Navy method estimate. DEXA is more accurate."
- Store `estimatedBF` in measurement entry for trending

**Edge cases:** Waist <= neck = "Cannot calculate". No height = show prompt. BF < 3% or > 60% = flag as likely error.

---

## Tier 3: Advanced Insights

### Build Order

```
Phase A (independent):
  15. Plateau Detection & Alerts
  16. Equipment Ceiling Alerts
  17. Consistency Streak Tracker
  18. AMRAP Final Set
  19. Deload Mode

Phase B (depends on Tier 1):
  20. Weekly Summary Card (needs #2, #7, #8, #17)
  21. Session Comparison View (needs #2)
  22. Volume by Muscle Group (needs #2)
```

---

### 15. Plateau Detection & Alerts [Medium]

**New function:** `detectPlateaus(dayName, exIndex)` — needs 4+ sessions. Checks last 3 sessions: if no weight increase AND no rep increase compared to the 4th-most-recent session, returns plateau info.

**`getSuggestion()`** — context-aware suggestions:
- At equipment ceiling: "Try slower tempo, pause reps, or 1.5 reps"
- Using Standard technique: "Try a different technique"
- Otherwise: "Consider a deload week"

**Rendering:** Amber warning badge in Progress view per plateaued exercise.

**CSS:** `.plateau-warning` amber border, `color: var(--text-warning)` (new CSS var).

**Edge cases:** Technique change mid-plateau = reset counter. <4 sessions = too early to detect. Intentional maintenance phase = could be false positive (only flag after 4+ sessions to reduce noise).

---

### 16. Equipment Ceiling Alerts [Small]

**New localStorage key:** `ironlog-equipment-max` (default: 50)

**Modifications:**
- `renderWorkout()`: if `ex.weight >= max`, show "At equipment max — progress via technique" badge
- Weight +5 button: if would exceed max, toast error and don't increase
- `renderSettings()`: add max weight input in "Workout" section

**Edge cases:** Max = 0 or blank = disable alerts. Different maxes per exercise = future enhancement, one global max for now.

---

### 17. Consistency Streak Tracker [Small]

**New function:** `getStreakData()` — walks backwards through weeks, counts sessions per week, tracks current streak (consecutive weeks with 4+ sessions), longest streak, total all-time sessions.

**Rendering:**
- Home view: streak badge below week counter: "X week streak" (only if >= 2)
- Toast at milestones (4, 8, 12, 26, 52 weeks) triggered in `finishWorkoutFinal()`

**Edge cases:** Current week included if already has 4+ sessions. No history = 0, no badge. Partial week = optimistic counting.

---

### 18. AMRAP Final Set [Small]

**Data change:** Add `amrap: true` flag to set objects in workout data.

**New function:** `toggleAMRAP(exIndex, setIndex)` — toggles `amrap` flag on set, re-renders.

**Rendering:**
- Small "AMRAP" toggle button on each set row in workout view
- When active: gold highlight, "AMRAP" label
- `getProgressData()`: add `amrapReps` field (reps from AMRAP set)
- Exercise progression charts: optional third series for AMRAP reps over time

**Edge cases:** Multiple AMRAP sets per exercise = allowed, chart tracks last one. 0 reps = skip. Old sessions = no AMRAP data, gaps in chart.

---

### 19. Deload Mode [Small]

**State:** `localStorage('ironlog-deload')` = `{active, startDate, originalWeights}`

**New functions:**
- `activateDeload()` — snapshot current weights for all exercises, store, toast
- `deactivateDeload()` — remove deload state, toast

**Modifications:**
- `startWorkout()` (line 614): if deload active, reduce weight by 40% (run through `snapWeight()` for 5 lb grid)
- `renderHome()`: if active, show banner with "End Deload" button. Auto-prompt after 7 days.
- `renderSettings()`: activate/deactivate button in "Workout" section.

**Edge cases:** Manual weight change during deload = allowed. >7 days = prompt, don't auto-deactivate. `snapWeight()` enforces 5 lb grid.

---

### 20. Weekly Summary Card [Medium]

**Depends on:** #2 Volume, #7 Difficulty, #8 PRs, #17 Streaks

**New function:** `getWeeklySummary(weekOffset)` — aggregate sessions, volume, PRs, avg difficulty, checklist score for a given week.

**Rendering on Home view:** Card showing previous week's stats: sessions, total volume, new PRs, avg difficulty, checklist score. Only show if previous week has data. Stats row uses same pattern as Settings stats (lines 1218-1221).

**Edge cases:** No data for previous week = don't show. Partial Tier 1 features = show available stats, omit missing.

---

### 21. Session Comparison View [Medium]

**State:** `state.compareBase`, `state.compareTarget` — each `{date, dayName}` or null.

**UX flow:**
1. History view: "Compare" button on each session
2. Select base session → show picker for same workout day sessions
3. Select target → render side-by-side comparison

**New function:** `renderComparison()` — 3-column layout (base | delta | target) per exercise. Color-coded deltas.

**Edge cases:** Different exercise counts (program changed) = only compare common exercises. Incomplete data = show "—". Same session selected twice = disable.

---

### 22. Volume by Muscle Group [Medium]

**New constant:** `MUSCLE_GROUPS` mapping exercise names to muscle groups. `GROUP_CATEGORIES` mapping push/pull/legs.

**New function:** `getWeeklyMuscleVolume(weekOffset)` — aggregate sets and volume per muscle group for a given week.

**Rendering in Progress view:** Bar chart or table of weekly sets per muscle group. Color-coded: green >= 10 sets, yellow 6-9, red < 6. Push/pull/legs split summary.

**Edge cases:** Unmapped exercise = console warn, skip. No workouts = empty message. Double-counting across muscle groups is intentional (reflects actual stimulus).

---

## Someday / Maybe

- **Rest Time Performance Correlation** [Medium]
- **Predicted Strength Milestones** [Medium]
- **Year-in-Review Summary** [Medium]
- **Milestone Timeline** [Medium]
- **Custom Program Editor** [Large] *(delay until program plateaus)*
- **DEXA Scan Tracker** [Medium] *(delay until next scan)*
- **Export to CSV** [Small]

## Cut List

- Warm-Up Set Tracking
- Workout Notes / Session Journal (per-session)
- Exercise Swap / Variations
- Superset Support
- Recomp Dashboard
- Goal Targets & Progress Bars
- FFMI Reference Chart
- Progress Photo Timeline
- Exercise Search & Filter in History

---

## Risk Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data migration v2-to-v3 corrupts data | High | Backup to `ironlog-data-v2-backup`, validate shape |
| SVG charts slow with 100+ points | Medium | LTTB sampling to ~50 points, IntersectionObserver |
| Nav bar overflow with 3 items | Medium | Reduce gap, test on 320px, cap at 4 items |
| localStorage quota (5MB) | Low | Size monitor in Settings, body data ~500KB/year |
| DOM rebuild destroys charts | High | SVG as string avoids this entirely |
| Undefined fields on old sessions | Medium | `|| defaultValue` patterns throughout |
| Auto-rest annoyance | Low | Settings toggle, skip on last set |
| Muscle group mapping gaps | Low | Console warn, map all PROGRAM exercises |
| Deload weight rounding | Low | `snapWeight()` enforces 5 lb grid |

## Rollback Strategy

- **Data migration**: v2 backup to `ironlog-data-v2-backup`
- **Git commits**: Per-feature, revertable independently
- **Service worker**: Cache version bump forces PWA update
- **Cloud sync**: `previous` endpoint for one-write-ago rollback
- **JSON backup**: User can always import from last export

## Bonus Enhancements

- **localStorage size display** in Settings
- **Progress view desktop layout** improvement with charts
- **Data shape validation** in `loadData()`
- **Extract `renderNavBar()`** shared function

## Testing Strategy

**Per-feature:** Functional, empty state, dark + light themes, desktop + iPhone, data persistence, cloud sync, migration.

**Charts:** 0 pts (empty msg), 1 pt (dot), 5-20 (normal), 50+ (LTTB), responsive sizing.

**Body data:** Decimals, range validation, same-day overwrite, rolling average with gaps.

## Post-Implementation Updates

- **CLAUDE.md**: v3 format, SVG pattern, Body view, nav, Settings sections
- **Memory**: SVG-in-DOM-rebuild pattern, v3 migration, nav constraints, muscle mapping
- **Service worker**: Bump cache per deploy
