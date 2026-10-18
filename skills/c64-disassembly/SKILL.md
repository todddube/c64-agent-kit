---
name: c64-disassembly
description: Disassemble and reverse-engineer Commodore 64 binaries (.prg, .d64, .crt, .t64, VICE snapshots) into rebuildable KickAssembler source, using Regenerator 2000 (headless export, label import, MCP server, live VICE link) and the VICE monitor. Use when the user has a C64 program without source and wants to understand, annotate, patch or rebuild it, when tracing what an existing demo/game does, or when disassembler output in 64tass/ACME/ca65 syntax needs to become KickAssembler.
---

# C64 disassembly and reverse engineering

## Tools

| Tool | Use it for |
|---|---|
| **Regenerator 2000** (`regenerator2000`, github.com/ricardoquesada/regenerator2000) | the main disassembler: code/data analysis, labels, comments, export to KickAssembler/64tass/ACME/ca65, MCP server |
| VICE monitor (`c64-vice-debugging` skill) | what the code does **at run time**: which addresses execute (`trace`, `chis`), what is code vs data, memory after a depacker has run |
| `c64.py peek` (`c64-toolchain`) | dump memory after unpacking, at an exact time |
| `c1541` (ships with VICE) | list and extract files from `.d64`: `c1541 disk.d64 -list`, `-read "name" out.prg` |

`c64.py doctor` reports whether Regenerator is installed (`C64_REGENERATOR` overrides the path).

## Fast path: binary → KickAssembler source that rebuilds

```sh
regenerator2000 game.prg --export_asm game.asm --assembler kick
python3 <c64-toolchain>/scripts/c64.py build game.asm --odir /tmp/re
cmp /tmp/re/game.prg game.prg && echo identical
```
- Run without a terminal (as agents do), the export is still written. The TUI then fails to
  start with `Device not configured`, which is harmless.
- `--headless` (no TUI at all) only accepts a saved `.regen2000proj`.
- **Always do the round-trip check.** A byte-identical rebuild proves the source is
  complete before you start editing it. (Tested: the `c64-demo-framework` template comes
  back identical.)
- With labels from a build you own: `--import_lbl main.vs` (KickAssembler `-vicesymbols`
  output, VICE label format). `--export_lbl` writes labels back out.
- `--verify` does the export → assemble → diff loop itself on a project file.

## Method for an unknown binary

1. **Load address and entry.** The first two bytes of a `.prg` are the load address. If it
   is `$0801`, the start is a BASIC `SYS` line: decode the digits after the `$9E` token.
2. **Packed?** Most released programs are crunched (Exomizer and others): a short decruncher
   followed by high-entropy bytes. Don't disassemble that. Run it in VICE until it jumps to
   the real entry (`c64.py mon prog.prg --seconds 3 -c "chis 30"` shows where it's
   executing), then dump the unpacked memory with `save "out.prg" 0 start end` and
   disassemble that instead.
3. **Separate code from data.** Static analysis guesses; run time knows. In VICE,
   `trace exec start end` (or `prof on` … `prof flat`) shows which addresses execute.
   Everything that never executes is data: tables, sprites, charsets, music, text.
4. **Recognise the usual landmarks.** Writes to `$D012`/`$D01A` plus `$0314/$FFFE` set up a
   raster IRQ. A `jsr` into `$1000`/`$1003` is usually a PSID-style player (init/play). Data
   behind `$D018` writes is charset/screen, behind sprite pointers (screen+`$3F8`) sprites.
   Use the `c64-hardware` skill to decode each register write.
5. **Name things** as you understand them (in the Regenerator TUI or project, or by editing
   the exported source) and re-run the round-trip after each batch of edits.
6. **Save a `.regen2000proj`** for anything you'll come back to: it keeps the labels,
   comments and data-type annotations, and it's what `--headless` needs.

## Interactive and agent-driven modes

```sh
regenerator2000 game.prg                         # TUI (for the user)
regenerator2000 --mcp-server-stdio               # MCP server for an agent (stdio)
regenerator2000 --mcp-server                     # MCP over HTTP, port 3000
x64sc -binarymonitor -binarymonitoraddress ip4://127.0.0.1:6502 -autostart game.prg &
regenerator2000 game.prg --vice localhost:6502   # live link to a running VICE
```
To give an agent the MCP server, register `regenerator2000 --mcp-server-stdio` in that
tool's MCP configuration (Claude Code: `claude mcp add regenerator -- regenerator2000
--mcp-server-stdio`; other tools have an equivalent `mcp` config entry).

## Syntax pitfalls

Exported or third-party disassembly is often in 64tass syntax (`;` comments, `label =
$xxxx`, `.byte`/`.word` with different directives). It does **not** build with
KickAssembler. Re-export with `--assembler kick`, or see the `c64-kickassembler` skill for
the conversion list.

## Respect the source

Disassembling to learn, fix your own lost source, or preserve software is common
practice in the C64 scene. Republishing someone else's program as your own is not; keep
original credits in anything you release.
