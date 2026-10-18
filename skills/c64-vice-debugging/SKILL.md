---
name: c64-vice-debugging
description: Debug and profile Commodore 64 programs in the VICE emulator's machine-code monitor - breakpoints and watchpoints with conditions on raster line (RL) and cycle (CY), labels from KickAssembler (-vicesymbols / ll), CPU history, the stopwatch, the built-in profiler (prof), I/O register dumps, memory/sprite views, keyboard injection, and scripted non-interactive runs. Use when a C64 program crashes, hangs, shows garbage, or misses its frame budget and you need to see what the CPU and VIC are actually doing, or to measure how many cycles or raster lines a routine or IRQ takes.
---

# Debugging C64 programs in VICE

Agents drive the monitor **headless** with `c64.py mon` from the `c64-toolchain` skill.
It starts VICE on a free port, runs the program to an exact emulated time, runs your
monitor commands in order, prints VICE's answers, and kills only its own VICE. `x` (or
`g`/`until`) resumes the machine and waits for the next checkpoint to stop it.

```sh
C64PY build main.asm --vicesymbols --odir /tmp/dbg          # main.prg + main.vs labels
C64PY mon /tmp/dbg/main.prg --seconds 1 --labels /tmp/dbg/main.vs \
    -c "break exec .main_loop" -c x -c "sw reset" -c x -c sw -c r
```
That is a real measurement of one main-loop pass (tested on the `c64-demo-framework`
template). Output:
```
#1 (Stop on  exec 084c)  251/$0fb,  52/$34          <- raster line 251, cycle 52
.C:084c  20 57 08    JSR .wait_frame - A:FF X:04 Y:08 SP:ff N.-..I..      17094
Stopwatch:      17094                                <- one NTSC frame (19656 with --pal)
```
(`C64PY` = `python3 <c64-toolchain skill>/scripts/c64.py`.) Add `--pal` / `--ntsc` to pick
the standard, and `--timeout S` for how long `x` may wait for a checkpoint (default 10 wall
seconds; on timeout it breaks in and says so).

The user can also debug interactively: `C64PY run prg`, then open the monitor from VICE's
menu (Alt+H by default). An agent can't type into that window, so it uses `mon`.

The full monitor command reference, checked against VICE 3.x's own `help`, is in
**`references/monitor.md`**. `--labels` loads the `.vs` file that `build --vicesymbols`
writes (VICE `add_label` format), so `.main_loop`, `.irq_top` etc. work in every command
and disassembly shows your names.

## Measuring time

| Question | Technique |
|---|---|
| Cycles a routine takes | `-c "break exec .check_exit" -c x -c "sw reset" -c del -c ret -c sw`: stop at entry, zero the stopwatch, drop the breakpoint, run to its `rts`. (Tested: 26 cycles for the template's `check_exit`, matching a hand count) |
| Which raster line an IRQ starts/ends on | `break exec .irq_top` / `.irq_end`, then read `LIN` and `CYC` in `r`, or put a condition on `RL` (raster line) and `CY` (cycle): `-c "break exec .irq_end if RL > \$f0" -c x` only stops on an overrun. The stop line prints `251/$0fb, 52/$34`: raster line, cycle |
| Where the frame's time goes | `prof on`, run a few seconds, `prof off`, `prof flat 20` (self time per function, by label) |
| Does the frame fit NTSC | instrument the main loop to store `$D012` (and `$D011` bit 7) when the work finishes, then `peek --mem` it on `--ntsc` and `--pal` |

Budgets: 17095 cycles a frame on NTSC (65 a line), 19656 on PAL (63 a line). A badline
leaves ~20-23 cycles.

## Symptom → first thing to check

| Symptom | Look at |
|---|---|
| Garbage characters / wrong charset | `io d000` → `$D018`; `m dd00 dd00` (VIC bank, inverted); is the charset at `$1000-$1FFF` in bank 0/2 (ROM shadow)? |
| Blank screen | `$D011` bit 4 (DEN); border = background; sprites only? |
| Sprites missing/wrong shape | `$D015`, pointers at screen+`$3F8`, `ms` on the data address, `$D010` for X > 255 |
| Hang right after start | `chis 50` after breaking in: stuck in a raster wait for a line that doesn't exist (> `$106` on NTSC)? |
| IRQ fires constantly / machine crawls | `$D019` not acknowledged; `io d000`; `break exec` on the handler and watch how often it hits |
| Silent SID | `io d400`: `$D418` volume, gate bits in `$D404/$D40B/$D412`, ADSR |
| Crash on exit | does `exit_demo` `rts` to BASIC or `cli` before `jmp ($fffc)`? |
| Memory being stomped | `watch store $xxxx`, then `chis` at the hit shows who wrote it |
| Music too fast on NTSC | PAL tune called every 60 Hz frame; see `c64-demo-framework` |

## Rules for agents
- Never `pkill`/`killall x64sc`; other agents may be running VICE. Kill only the process
  you started (`c64.py` does this for you).
- Never `sleep` waiting for an emulator state. Use `-limitcycles`, `c64.py peek --seconds`,
  or a breakpoint.
- Use a free port for `-remotemonitor`/`-binarymonitor` (`-remotemonitoraddress
  ip4://127.0.0.1:<port>`), never a fixed 6510/6502, so parallel runs don't collide.
