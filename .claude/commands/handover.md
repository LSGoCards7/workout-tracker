Generate a session handover document that captures the full context of this conversation for a future Claude Code session.

## Instructions

1. **Review the full conversation history** from this session — every message, tool call, decision, error, and resolution.

2. **Determine the output filename:**
   - Use the Glob tool to check for existing `HANDOVER-*.md` files in `handovers/`
   - Today's date in YYYY-MM-DD format determines the base name: `HANDOVER-YYYY-MM-DD.md`
   - If that file already exists, append a counter: `HANDOVER-YYYY-MM-DD-2.md`, then `-3.md`, etc.
   - Never overwrite an existing handover file

3. **Write the handover document** using the Write tool to save it to the `handovers/` directory. Use this exact structure:

```markdown
# Session Handover — YYYY-MM-DD

## Session Summary
What was being worked on and what got done. Be specific — name the features, files, and outcomes.

## What Worked / What Didn't
Bugs encountered, failed approaches, dead ends, and how they were resolved. This is the most valuable section for avoiding repeated mistakes.

## Key Decisions
Architectural or design decisions made during this session and the reasoning behind them. Include alternatives that were considered and rejected.

## Lessons Learned & Gotchas
Anything the next session's Claude should watch out for. Include environment quirks, API behavior surprises, or domain-specific insights discovered.

## Next Steps
- [ ] Clear, actionable items for the next session
- [ ] Include enough context that someone unfamiliar could pick these up

## Important Files Map
Files created, modified, or particularly relevant to continue the work. Include brief descriptions of what each file does or what changed.

## Current State
Is anything broken? Are tests passing? Any uncommitted changes? What branch are we on? Summarize the health of the codebase.
```

4. **Report back** to the user with the filename and a one-line confirmation.

## Important

- Be thorough but concise — aim for a document that takes 2-3 minutes to read
- Focus on information that would be LOST when session context resets
- Don't include generic project info already in CLAUDE.md — focus on session-specific context
- Include specific file paths, line numbers, error messages, and code snippets where relevant
- If the session was short or uneventful, say so — a short handover is fine
