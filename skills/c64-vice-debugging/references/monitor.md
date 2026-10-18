# VICE monitor reference

Checked against the `help` output of VICE 3.x (x64sc). Commands take hex by default
(`$` optional); `.label` refers to a loaded label. Abbreviations in parentheses.

Agents run these headless with `c64.py mon PRG --seconds S -c CMD -c CMD ...` (see the
`c64-toolchain` skill). One `-c` per command, in order.

## Machine state

| Command | Does |
|---|---|
| `registers` (`r`) | A X Y SP, `$00/$01`, flags, raster `LIN`, `CYC` in line, stopwatch |
| `stopwatch` (`sw`) / `sw reset` | CPU cycle counter / zero it |
| `cpuhistory` (`chis`) `[count]` | the last *count* executed instructions: how did we get here |
| `step` (`z`) / `next` (`n`) `[count]` | one instruction; `n` steps over `jsr` |
| `return` (`ret`) | run until the current subroutine's `rts`/`rti` |
| `goto` (`g`) `addr` | continue at an address |
| `exit` (`x`) | resume the machine |
| `until` (`un`) `addr` | temporary breakpoint at *addr*, then resume |
| `backtrace` (`bt`) | the JSR call chain |
| `bank` `[name]` | which memory view `m`/`d` read: `cpu` (default, as the CPU sees it), `ram`, `rom`, `io`, `cart` |
| `reset` `[0\|1]` | 0 = reset, 1 = power cycle |
| `keybuf "text"` | put text into the C64's keyboard buffer |
| `warp` `[on\|off]` | warp mode |

## Memory

| Command | Does |
|---|---|
| `mem` (`m`) `start [end]` | hex + PETSCII dump |
| `disass` (`d`) `[start [end]]` | disassemble (shows labels when loaded) |
| `io` `[addr]` | decoded I/O chips: `io d000` VIC, `io d400` SID, `io dc00` CIA 1, `io dd00` CIA 2 |
| `memsprite` (`ms`) `addr` | show memory as a sprite bitmap |
| `memchar` (`mc`) `addr` | show memory as characters |
| `screen` (`sc`) | the text screen as the VIC sees it |
| `fill` (`f`) `start end bytes` | fill memory |
| `>` `addr bytes` | write bytes |
| `hunt` (`h`) `start end bytes` | search memory |
| `compare` (`c`) / `move` (`t`) | compare / copy ranges |
| `a` `addr` | assemble in place |
| `save` (`s`) `"file" 0 start end` / `load` (`l`) `"file" 0 [addr]` | save/load memory to/from the host |

## Checkpoints

| Command | Does |
|---|---|
| `break` (`bk`) `[load\|store\|exec] addr [addr] [if cond]` | stop (exec by default) |
| `watch` (`w`) `[load\|store] addr [addr] [if cond]` | stop on memory access (load+store by default) |
| `trace` (`tr`) `[...] addr [addr]` | print and continue, don't stop |
| `condition` (`cond`) `n if cond` | add a condition to checkpoint *n* |
| `command` `n "cmd"` | run a monitor command when *n* hits (not `x`) |
| `ignore` `n [count]` | skip the next *count* hits |
| `enable`/`disable`/`delete` (`en`/`dis`/`del`) `[n]` | manage checkpoints (no *n* = all) |

**Conditions** compare registers `A X Y PC SP FL`, **`RL` (raster line)** and **`CY`
(cycle within the line)** with `== != < > <= >=`, combine with `&& ||` and arithmetic, and
can read memory in a bank: `if @io:$d019 & $01 == $01`. Examples:

```
break exec .irq_end if RL > $f0          # the IRQ finished too late
watch store $d020                         # who changes the border colour?
break exec .main_loop if RL < $f8         # main loop started before line 248
trace exec .music_play                    # how often does music play run
```

## Profiling

| Command | Does |
|---|---|
| `prof on` / `prof off` | start (and clear) / stop profiling |
| `prof flat [n]` | top *n* functions by self time |
| `prof graph [ctx] [depth d]` | call graph |
| `prof func .name` | callers, callees and totals for one function |
| `prof disass .name` | per-instruction cycle counts for one function |

Headless: `-c "prof on" -c "until .some_later_point" -c "prof off" -c "prof flat 15"`,
or let a breakpoint stop the run after enough frames.

## Labels and files

| Command | Does |
|---|---|
| `load_labels` (`ll`) `"file.vs"` | load labels (KickAssembler `-vicesymbols` writes this format) |
| `add_label` (`al`) `addr .name` / `show_labels` (`shl`) | add / list labels |
| `screenshot` (`scrsh`) `"file" 2` | screenshot; format 2 = PNG |
| `dump` / `undump` `"file"` | save / restore a full machine snapshot |
| `record` / `playback` `"file"` | record / replay monitor commands |

## Useful x64sc command-line options

| Option | Does |
|---|---|
| `-ntsc` / `-pal` | video standard (default is PAL) |
| `-autostart prg` | load and RUN |
| `-warp` | as fast as the host allows |
| `-limitcycles N` | quit after N cycles (never hangs a script) |
| `-exitscreenshot file.png` | screenshot on quit |
| `-moncommands file` | run monitor commands at start-up |
| `-initbreak addr` | open the monitor at an address |
| `-keybuf "text"` | type after boot |
| `-remotemonitor -remotemonitoraddress ip4://127.0.0.1:PORT` | text monitor over TCP (what `c64.py` uses) |
| `-binarymonitor -binarymonitoraddress ...` | binary monitor protocol (for IDE debuggers, Regenerator 2000 `--vice`) |
