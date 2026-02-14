# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IRON LOG — a dumbbell hypertrophy workout tracking PWA. The entire application is a single self-contained HTML file (`iron_log.html`) with inline CSS and JavaScript. No build system, no dependencies, no backend.

## Development

- **Run**: Open `iron_log.html` directly in a browser
- **No build/lint/test commands** — there is no package.json, no bundler, no test framework
- **All changes** are made directly to `iron_log.html`

## Architecture

### Single-file structure (`iron_log.html`)
The file is organized in order: `<style>` → `<div id="app">` → `<nav>` → `<script>`.

### State machine rendering
- Global `state` object tracks current view, selected workout, active exercise, etc.
- `render()` function reads `state` and rebuilds `#app` innerHTML
- Navigation between views: update `state.view` then call `render()`
- Views: `home`, `workout`, `history`, `progress`, `settings`
- `renderTimer()` updates `#rest-timer` independently (fixed overlay, outside `#app`)

### Data persistence
- All data stored in browser LocalStorage under key `ironlog-data`
- v2 format: `{ version: 2, history, checklist, lastExportDate, backupDismissDate }`
- Auto-migration from v1 (no version field) with safety backup to `ironlog-data-v1-backup`
- `saveData()` writes to LocalStorage; `loadData()` reads on startup
- Export/import JSON with merge vs replace flow
- Data shape:
  - `history["YYYY-MM-DD"]["Day Name"][exerciseIndex]` → `{ weight, technique, sets: [{reps, completed}], notes }`
  - `checklist["YYYY-Www"][itemIndex]` → completed item indices

### Program structure
- 5-day dumbbell split: Lower A, Upper A, Lower B, Upper B, Day 5
- Weekly schedule: Sat/Sun/Tue/Thu/Fri workout days, Mon/Wed rest
- Exercises defined in `PROGRAM` array with name, sets, rep range, default weight, tempo, rest time
- Techniques: standard, dropset, myorep, superset, slow eccentric

### Styling
- Dark theme: background `#0f172a`, text `#e2e8f0`, accent `#4ade80`
- JetBrains Mono font throughout
- Mobile-first, max-width 480px, fixed bottom nav bar
- Responsive breakpoints: 768px (tablet, 720px max), 1200px (desktop, 1000px max)
- iOS PWA meta tags for home screen installation

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
