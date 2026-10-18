---
name: c64-demo-framework
description: "Start or restructure a Commodore 64 demo, intro or game that takes over the machine - a tested KickAssembler skeleton (sei, CIA/NMI masking, RESTORE-proof NMI vector, NTSC/PAL detection, frame loop, RUN/STOP exit through the KERNAL reset vector), plus how to keep PAL SID music at the right tempo on NTSC, open the top/bottom border, blank the screen for reveals, and lay out memory around a non-relocatable PSID tune. Use when scaffolding a new C64 project, adding music or a frame loop, porting a PAL demo to NTSC, or when a demo crashes on exit, ignores RUN/STOP, or plays music too fast."
---

# C64 demo framework

## Start from the template

`templates/main.asm` is a complete, tested program (assembled and run on NTSC and PAL in
VICE). Copy it to the new project as `main.asm` and replace the two marked sections:

```sh
mkdir -p mydemo && cp <this skill>/templates/main.asm mydemo/main.asm
python3 <c64-toolchain skill>/scripts/c64.py build mydemo/main.asm
python3 <c64-toolchain skill>/scripts/c64.py shot mydemo/bin/main.prg --seconds 1 --out /tmp/s.png
```
It shows `NTSC` or `PAL` at the top left. That one screenshot proves the build, the
autostart and the detection all work.

Optional shared includes, if the project wants a full set of named constants:
`templates/c64_constants.asm` (`VIC_`/`SID_`/`CIA_`/KERNAL labels) and `templates/zeropage.asm`
(a zero-page allocation). Copy them into the project and `#import` them, so the project
still builds from a fresh clone. The template defines a few labels of its own; delete any
that the include also defines, or KickAssembler reports a duplicate.

## What the skeleton guarantees, and why

| Piece | Why it is there |
|---|---|
| `sei`, then `$7F` → `$DC0D` and `$DD0D` and read back | stops KERNAL IRQs and CIA 2 NMIs; the read acks anything already latched |
| NMI vector `$0318` → `rti`, in one store | RESTORE is wired straight to `/NMI`; without this, RUN/STOP+RESTORE warm-starts BASIC on top of a zero page the demo has overwritten. With the KERNAL banked out, set `$FFFA/$FFFB` as well |
| `detect_video` | sets `ntsc` from the highest raster line seen (NTSC tops out at `$106`) |
| `wait_frame` on line 250 | line 250 exists on both standards, and its low byte occurs once a frame on both. Waiting to *leave* the line stops a short frame's work running twice |
| `check_exit` every frame | RUN/STOP (row `$7F`, bit 7) quits |
| `exit_demo` → `jmp ($fffc)`, **no `cli`** | BASIC's zero page is gone, so `rts` would crash. `$fffc` does its own `sei`; a `cli` before it lets an IRQ run the KERNAL handler on garbage. If the demo left the bytes `CBM80` at `$8004`, the reset starts *that* as a cartridge: clear them |

## Going further

- **Music, NTSC vs PAL, frame budgets**: `references/video-standards.md`. Covers the PAL
  tune that plays 20% fast on NTSC, the 5-in-6 tick fix, and keeping beat-synced timers on
  the beat.
- **Opening the top/bottom border, blanking the screen for reveals, the `$3FFF` idle
  byte, sprite ghosts below Y=56**: `references/borders-and-blanking.md`.
- **Raster IRQs instead of polling**: the IRQ checklist in the `c64-code-review` skill
  (acknowledge `$D019`, bit 8 of the compare line, vector at `$0314` or `$FFFE` to match
  banking, preserve A/X/Y).

## Memory layout tips

- A PSID tune is **not relocatable**: it loads at its own address (often `$1000`). Check it
  with `.print toHexString(music.location)` and plan around it.
- In bank 0 the VIC sees character ROM at `$1000-$1FFF`, so a tune at `$1000` costs no
  graphics space, but sprites and charsets cannot go there.
- When code, music, sprites and charsets don't all fit below `$4000`, move the code (e.g.
  `* = $4000`) rather than the VIC bank. The `BasicUpstart2` stub can `SYS` anywhere.
- Build once with `-- -showmem` to check segment placement, then drop the flag.
