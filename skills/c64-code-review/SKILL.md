---
name: c64-code-review
description: Review Commodore 64 6502/6510 assembly for hardware and CPU correctness against a fixed checklist - 6502 arithmetic and branching, memory banking and zero page, VIC-II bank/$D018/sprite setup, raster IRQ handling and NTSC/PAL frame budgets, SID and CIA usage, NMI/RESTORE and clean exit. Use after writing or changing C64 assembly, before committing it, or when a C64 program misbehaves in VICE or on real hardware (garbage graphics, blank screen, IRQ lockup, silent SID, crash on exit, wrong speed on NTSC). Works as a review the main agent runs, or as the brief for a subagent if the tool supports them.
---

# C64 code review

You check code against the hardware, not against intuition. Every finding names a
register, a value, and what the chip actually does with it.

## Scope and mode

Pick a mode (STATIC if nobody said):

| Mode | What you do | Budget |
|---|---|---|
| **STATIC** (default) | Read, trace values, build once into a scratch dir. No emulator. | ~25 tool calls |
| **MEASURED** | STATIC, plus emulator runs to *confirm named* suspicions or measure a named budget | ~45 tool calls |
| **FOLLOW-UP** | Only the diff since the last review (`git diff`), plus whatever the diff can break | ~15 tool calls |

- Review at most ~1000 lines of source per pass. Split a bigger change into passes (or
  subagents).
- **Target video standard**: use what the project says. If it doesn't say, check NTSC
  first (17095 cycles a frame) and PAL second (19656). Code that fits only a PAL frame is
  a defect for NTSC users, not a caveat.
- Stay inside the scope you were given. Anything you notice outside it gets one line under
  "Out of scope".
- **Read and build only; do not edit source.** Report, and let the caller decide.

## Method

1. Read the files under review in full, including header comments. Well-written C64
   source documents its memory layout and invariants; a "bug" that contradicts a stated
   invariant is usually a misreading.
2. Work through **`references/checklist.md`** in order. Don't skip a section because the
   code looks fine: the VIC bank and IRQ-acknowledge items in particular fail silently.
   For register details, open the `c64-hardware` skill's references; for syntax, the
   `c64-kickassembler` skill.
3. For each candidate, trace the actual values: which register, which value, what the
   chip does. "This looks wrong" is not a finding.
4. Verify by building into a **scratch directory**, never the project's `bin/`:
   `python3 <c64-toolchain>/scripts/c64.py build file.asm --odir <scratch>`
5. MEASURED only: confirm with `c64.py peek` (an instrumented scratch build that leaves its
   numbers in memory, read with `--mem`) or the `c64-vice-debugging` skill (raster-line
   breakpoints, `prof`). Never write your own emulator harness, never `sleep`-poll VICE,
   never `pkill x64sc`.
6. Once the findings are confirmed, stop and report. A clean section needs one sentence.

## Report

Order by severity. For each finding:

- `file.asm:line`
- **What the code does**: the literal CPU/register behaviour
- **What was intended**: from the comments and surrounding code
- **Symptom**: what the user would see or hear (garbage charset, frozen machine, no sound,
  crash on RUN/STOP, music too fast on NTSC)
- **Fix**: concrete and minimal, in the project's assembler syntax

Keep confirmed defects apart from style/robustness suggestions. Give the video standard
for every timing finding. Say plainly what you could not verify (real hardware only,
6581 vs 8580 filter differences). Keep the whole report under ~800 words: defects in
full, nits as one-liners.

## As a subagent

Tools with subagents (Claude Code, Codex, Copilot CLI and others) can run this review in
an isolated context. Give the subagent: the mode, the files (≤ ~1000 lines), the target
standard, and "follow the c64-code-review skill". The repo's `agents/` folder has a
ready-made Claude Code subagent definition.
