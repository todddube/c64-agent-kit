---
name: c64-kickassembler
description: "Write, read and fix Commodore 64 6502 assembly in KickAssembler (v5.x) syntax - directives (.byte, .fill, .label, .const, .macro, .pseudopc, .segment, .import binary, #import), the script language, BasicUpstart2, PSID/Koala import, illegal opcodes, and KickAssembler's error messages. Use whenever a .asm file is KickAssembler source (// comments, .label, BasicUpstart2, #import), when a KickAssembler build fails, or when converting 64tass/ACME/ca65 source to KickAssembler. Trigger on \"KickAss\", \"Kick Assembler\", \"jump distance is too far\", \"Unknown symbol\", \".fill\", \".macro\"."
---

# KickAssembler

The full directive table, syntax notes, colour constants and command-line options are in
**`references/directives.md`**. Read it rather than recalling syntax. The authority beyond
that is the manual (`KickAssembler.pdf`, shipped next to `KickAss.jar`). To build, use the
`c64-toolchain` skill (`c64.py build`).

## Conventions

- Lowercase mnemonics (`lda`, `sta`); `$` hex, `%` binary, `#` immediate.
- `//` and `/* */` comments. `;` is **not** a comment: it means 64tass/ACME syntax.
- Constants: `.label SCREEN = $0400` (an address) or `.const DELAY = 7` (a number).
- Imports: `#import "file.asm"` (`.import source` is deprecated); `#importonce` at the top
  of a shared include.
- Program start: `BasicUpstart2(start)` emits a `SYS` stub at `$0801`; put code at `$0810`
  or later.
- Reusable local labels: `!loop:` / `!:` with `bne !loop-` (backward), `bne !+` (forward).
- Segments: `* = $4000 "Code"` names a block for `-showmem`.

## Idioms worth knowing

```kickass
.fill 256, round(127.5 + 127.5 * sin(toRadians(i * 360 / 256)))   // sine table at assembly time
rows: .lohifill 25, SCREEN + i * 40                                // row addresses: rows.lo,x / rows.hi,x
.var music = LoadSid("tune.sid")                                   // PSID import
* = music.location "Music"
.fill music.size, music.getData(i)
// call music.init with A = song, then jsr music.play once per (50 Hz!) tick
.align $100                                                       // page-align a table (no page-cross penalty)
.pseudopc $c000 { ... }                                            // assemble for a different run address
```

## Errors and what they mean

| Message | Cause | Fix |
|---|---|---|
| `relative address is illegal (jump distance is too far: -131)` | branch target > 127 bytes away | invert the test over a `jmp`: `beq skip / jmp far / skip:` |
| `Unknown symbol 'x'` | typo, label in another scope/namespace, or an `#import` missing | check `{}` scopes and namespaces (`ns.label`) |
| `Inputfile '-x' doesn't exist` / `Already have an inputfile` | a bad option, usually in `KickAss.cfg` (`-libdir=.` instead of `-libdir .`) | fix the cfg: options take their value after a space |
| `Can't open file` on `#import` | path is relative to the *importing* file (or `-libdir`) | fix the relative path |
| Code bigger than expected, 1 cycle slower | a forward-referenced zero-page label assembled as absolute | define zero-page labels (`.label ptr = $fb`) before the code that uses them |
| Output missing / empty file | code placed in a segment that no `.file`/default output includes | check `.segment` / `.segmentdef` usage |

## Gotchas

- Illegal opcodes are **enabled** by default. `.cpu _6502NoIllegals` rejects them.
- The script language is floating point; values are truncated when emitted. Wrap in
  `round()` where it matters.
- `<expr` / `>expr` are low / high byte. `lda #<label` loads the low byte.
- Text: `.encoding "screencode_upper"` (or `_mixed`) for screen RAM, `"petscii_upper"`
  for CHROUT. The default for `.text` is screencode mixed.
- A PSID tune written for PAL plays ~20% fast when called once per NTSC frame; see the
  `c64-demo-framework` skill (`c64-demo-framework/references/video-standards.md`).
- Disassembler output (Regenerator 2000, VICE, da65) often comes out in 64tass/ACME/ca65
  syntax. Re-export it as KickAssembler, or convert `;` → `//`, `label = $xxxx` →
  `.label label = $xxxx`, `!byte`/`.byt` → `.byte`, before building.
