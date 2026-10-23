---
name: c64-toolchain
description: "Build, run, screenshot and measure Commodore 64 programs with KickAssembler and the VICE emulator through one cross-platform script (scripts/c64.py - doctor, build, run, shot, peek, mon). Use whenever you assemble a C64 .asm file, launch or test a .prg in VICE, need to see what a demo renders at a given moment, read C64 memory or run VICE monitor commands at an exact emulated time, or set up / diagnose the C64 toolchain (Java, KickAss.jar, x64sc, c1541, petcat). Trigger on \"build this\", \"run it in VICE\", \"what does it look like after N seconds\", \"KickAss error\", \"x64sc\", \".prg\"."
---

# C64 toolchain: KickAssembler + VICE

Everything here goes through **`scripts/c64.py`** in this skill's directory (Python 3.8+,
standard library only; macOS, Windows, Linux). Use it instead of hand-written `java -jar`
lines, VICE monitor scripts or `sleep` loops: it already knows the tool paths, the output
filtering, the timing maths and how to clean up after itself.

Below, `C64PY` means `python3 <this skill's dir>/scripts/c64.py`. **On Windows** use
`py -3` (or `python`) instead of `python3`; every subcommand behaves the same there.
Paths may use `/` or `\`.

## 1. First: doctor

```sh
C64PY doctor          # finds java, KickAss.jar, x64sc, c1541, petcat, regenerator, exomizer
C64PY doctor --save   # remember the paths in ~/.config/c64-agent-kit/config.json
```
Exit status 1 means a required tool is missing; the output says where to get it. Paths
can always be forced with env vars: `C64_JAVA`, `C64_KICKASS_JAR`, `C64_X64SC`,
`C64_C1541`, `C64_PETCAT`, `C64_REGENERATOR`, `C64_EXOMIZER`. `C64_VIDEO=ntsc|pal` sets the
default video standard (NTSC unless set: its frame is the tighter budget).

## 2. Build

```sh
C64PY build path/to/main.asm                    # -> path/to/bin/main.prg
C64PY build main.asm --odir /tmp/scratch        # build somewhere else
C64PY build main.asm --vicesymbols              # also main.vs, labels for the VICE monitor
C64PY build main.asm -- -showmem                # anything after -- goes to KickAssembler
```
- **The .prg is named after the source file**: `main.asm` -> `bin/main.prg`,
  `scroller.asm` -> `bin/scroller.prg`. That is KickAssembler's default and the only
  naming convention; never pass `-o` to rename it, and never put `-o` in `KickAss.cfg`
  (it would force one fixed filename on every build on the machine). A project that
  wants a different name renames the source.
- A clean build prints **one line**: `Writing prg file: main.prg` (plus any deliberate
  `.print` output in the source). Anything else is an error or warning. The full,
  unfiltered output is always in `<odir>/buildlog.txt`. Exit status is non-zero on failure.
- KickAssembler runs with the source's directory as working directory, so `#import` paths
  resolve relative to the source.
- **When reviewing or experimenting, build into a scratch directory**, not the project's
  `bin/`: the user and other agents build there.
- Keep `-showmem`, `-symbolfile`, `-vicesymbols`, `-debug`, `-bytedump` for the one build
  that needs them. Don't add them to `KickAss.cfg`.
- `KickAss.cfg` beside the jar is read on every build. If *every* build suddenly fails with
  `Inputfile '-x' doesn't exist` / `Already have an inputfile`, look there: options take
  their value after a space (`-libdir .`, never `-libdir=.`).

Syntax questions, directives and error messages: see the `c64-kickassembler` skill.

## 3. Run

```sh
C64PY run bin/main.prg           # detached VICE window, -autostart, default standard
C64PY run bin/main.prg --pal     # the other standard
```
The log (`main.prg-vice.log`) always contains "Unknown disk image", "no CRT header" and
tape errors for a .prg. Those are autodetect probes, not failures; the line that matters is
`AUTOSTART: Loading PRG file ... with direct RAM injection`.

## 4. See and measure without watching

```sh
C64PY shot bin/main.prg --seconds 5 --out /tmp/f.png          # exact frame, ~3 s
C64PY peek bin/main.prg --seconds 3 --mem 0002 0014 --mem d011 d012
C64PY peek bin/main.prg --seconds 3 --pal --mem c000 c03f --shot /tmp/f.png
```
- `--seconds` counts from program start; `--boot N` (default 3200000 cycles) covers the
  C64 boot plus autostart. Boot grows with `.prg` size; if early frames look wrong, raise it.
- `shot` uses `-limitcycles`, so it is exact. `peek` stops within about a frame of the
  target and prints the cycle it actually stopped at.
- Open the PNG to look at it. This is the fastest way to check an intro, a raster split
  or a colour choice.
- **To measure something** (cycles used, a counter, which branch ran): build an
  instrumented copy into a scratch dir that leaves its numbers in memory, then read them
  with `--mem`. For interactive work (breakpoints, profiling, raster conditions) use the
  `c64-vice-debugging` skill.

### Rules that keep parallel agents from breaking each other
- `peek` picks a free monitor port per run and kills only the VICE it started. **Never
  `pkill`/`killall x64sc`**, and never run VICE on a fixed monitor port from a script.
- **Never `sleep` waiting for the emulator.** Ask for the emulated time you want.

## Timing facts used everywhere

| | NTSC (6567R8) | PAL (6569) |
|---|---|---|
| CPU clock | 1022727 Hz | 985248 Hz |
| Lines × cycles/line | 263 × 65 | 312 × 63 |
| **Cycles per frame** | **17095** | **19656** |
| Frame rate | 59.83 Hz | 50.12 Hz |
| VICE flag | `-ntsc` | `-pal` (VICE's default) |

A design that only fits a PAL frame is a bug for anyone in North America or Japan; check
NTSC first unless the project says it is PAL-only.

## Other VICE tools (found by `doctor`)

```sh
c1541 -format "demo,01" d64 demo.d64 -write bin/main.prg main    # disk image
c1541 demo.d64 -list
petcat -2 -o listing.txt -- prog.prg                              # detokenize BASIC
```
