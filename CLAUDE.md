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
- Views: `home`, `workout`, `history`, `progress`

### Data persistence
- All data stored in browser LocalStorage under key `ironlog-data`
- `save()` writes to LocalStorage; `load()` reads on startup
- Data shape:
  - `history["YYYY-MM-DD"]["Day Name"][exerciseIndex]` → `{ weight, technique, sets: [{reps, completed}], notes }`
  - `checklist["YYYY-Www"][itemIndex]` → completed item indices

### Program structure
- 5-day dumbbell split: Lower A, Upper A, Lower B, Upper B, Day 5
- Weekly schedule: Mon/Tue/Thu/Fri workout days, Wed/Sat/Sun rest
- Exercises defined in `PROGRAM` array with name, sets, rep range, default weight, tempo, rest time
- Techniques: standard, dropset, myorep, superset, slow eccentric

### Styling
- Dark theme: background `#0f172a`, text `#e2e8f0`, accent `#4ade80`
- JetBrains Mono font throughout
- Mobile-first, max-width 480px, fixed bottom nav bar
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
