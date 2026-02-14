#!/usr/bin/env python3
"""Pre-compact hook: generates a session handover document before auto-compaction.

Reads the transcript from stdin JSON, extracts conversation content, and uses
`claude -p` to generate a structured handover document.

Always exits 0 — PreCompact hooks must never block compaction.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

LOG_DIR = Path(__file__).parent
LOG_FILE = LOG_DIR / "handover.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("pre-compact-handover")


def get_next_filename(project_root: Path) -> Path:
    """Determine the next available HANDOVER-YYYY-MM-DD[-N].md filename."""
    handover_dir = project_root / "handovers"
    handover_dir.mkdir(exist_ok=True)
    today = date.today().isoformat()
    base = handover_dir / f"HANDOVER-{today}.md"
    if not base.exists():
        return base
    counter = 2
    while True:
        candidate = handover_dir / f"HANDOVER-{today}-{counter}.md"
        if not candidate.exists():
            return candidate
        counter += 1


def extract_conversation(transcript_path: str, max_chars: int = 50_000) -> str:
    """Extract conversation content from JSONL transcript, capped at max_chars."""
    path = Path(transcript_path)
    if not path.exists():
        log.warning("Transcript file not found: %s", transcript_path)
        return ""
    if path.stat().st_size == 0:
        log.warning("Transcript file is empty: %s", transcript_path)
        return ""

    messages = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                role = entry.get("role", "")
                if role not in ("user", "assistant"):
                    continue

                content = entry.get("content", "")
                if isinstance(content, list):
                    # Extract text blocks, skip tool_use/tool_result details
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                            elif block.get("type") == "tool_result":
                                # Include a brief note, not full output
                                text_parts.append("[tool result]")
                            elif block.get("type") == "tool_use":
                                tool_name = block.get("name", "unknown")
                                text_parts.append(f"[used tool: {tool_name}]")
                        elif isinstance(block, str):
                            text_parts.append(block)
                    content = "\n".join(text_parts)
                elif not isinstance(content, str):
                    content = str(content)

                if content.strip():
                    messages.append(f"**{role}:** {content}")
    except Exception as e:
        log.error("Error reading transcript: %s", e)
        return ""

    if not messages:
        return ""

    # Join all messages, then take the last max_chars
    full_text = "\n\n---\n\n".join(messages)
    if len(full_text) > max_chars:
        full_text = full_text[-max_chars:]
        # Find the first clean message boundary after truncation
        boundary = full_text.find("\n\n---\n\n")
        if boundary != -1:
            full_text = full_text[boundary + 7:]

    return full_text


HANDOVER_PROMPT = """\
You are generating a session handover document for a Claude Code session that is about to be compacted.

Below is the conversation transcript from the session. Analyze it and produce a structured handover document.

IMPORTANT:
- Be thorough but concise — aim for a document that takes 2-3 minutes to read
- Focus on information that would be LOST when session context resets
- Don't include generic project info — focus on session-specific context
- Include specific file paths, error messages, and code snippets where relevant
- If the session was short or uneventful, say so

Use this exact structure:

# Session Handover — {today}

## Session Summary
What was being worked on and what got done.

## What Worked / What Didn't
Bugs encountered, failed approaches, and how they were resolved.

## Key Decisions
Architectural or design decisions made and the reasoning behind them.

## Lessons Learned & Gotchas
Anything the next session's Claude should watch out for.

## Next Steps
- [ ] Clear, actionable items for the next session

## Important Files Map
Files created, modified, or relevant to continue the work.

## Current State
Is anything broken? Are tests passing? Any uncommitted changes?

---

CONVERSATION TRANSCRIPT:

{transcript}
"""


def main():
    try:
        # Read hook input from stdin
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            log.warning("No input received on stdin")
            return

        try:
            hook_input = json.loads(raw_input)
        except json.JSONDecodeError as e:
            log.error("Failed to parse stdin JSON: %s", e)
            return

        transcript_path = hook_input.get("transcript_path", "")
        cwd = hook_input.get("cwd", "")

        if not transcript_path:
            log.warning("No transcript_path in hook input")
            return

        if not cwd:
            log.warning("No cwd in hook input, using script parent")
            cwd = str(Path(__file__).resolve().parents[2])

        project_root = Path(cwd)
        if not project_root.is_dir():
            log.error("Project root is not a directory: %s", cwd)
            return

        # Check claude CLI is available
        if not shutil.which("claude"):
            log.error("claude CLI not found on PATH")
            return

        # Extract conversation content
        conversation = extract_conversation(transcript_path)
        if not conversation:
            log.warning("No conversation content extracted — skipping handover")
            return

        # Build the prompt
        today = date.today().isoformat()
        prompt = HANDOVER_PROMPT.format(today=today, transcript=conversation)

        # Call claude -p to generate the handover
        log.info("Calling claude -p to generate handover...")
        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "text"],
                capture_output=True,
                text=True,
                timeout=100,
                cwd=cwd,
            )
        except subprocess.TimeoutExpired:
            log.error("claude -p timed out after 100s")
            return
        except FileNotFoundError:
            log.error("claude CLI not found when executing")
            return

        if result.returncode != 0:
            log.error("claude -p failed (exit %d): %s", result.returncode, result.stderr[:500])
            return

        output = result.stdout.strip()
        if not output or len(output) < 50:
            log.warning("claude -p produced empty or very short output (%d chars)", len(output))
            return

        # Write the handover file
        output_path = get_next_filename(project_root)
        try:
            output_path.write_text(output, encoding="utf-8")
            log.info("Handover written to %s (%d chars)", output_path.name, len(output))
        except OSError as e:
            log.error("Failed to write handover file: %s", e)
            return

    except Exception as e:
        log.error("Unexpected error in pre-compact-handover: %s", e, exc_info=True)


if __name__ == "__main__":
    main()
    sys.exit(0)
