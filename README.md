# c64-agent-kit

Agent Skills for writing, building, debugging and reverse-engineering **Commodore 64 6502
assembly** with an AI coding agent, using **KickAssembler**, the **VICE** emulator and
**Regenerator 2000**.

The skills use the open [Agent Skills](https://agentskills.io) format (a folder with a
`SKILL.md`), so the same files work in **Claude Code, OpenAI Codex, Cursor, GitHub Copilot,
Gemini CLI and opencode**, and in any other agent that reads `SKILL.md`.

By RetroDubTRVA.

## What's in it

| Skill | What your agent can do with it |
|---|---|
| [`c64-toolchain`](skills/c64-toolchain/SKILL.md) | find the tools (`doctor`), **build** with KickAssembler showing only what matters, **run** in VICE, take a **screenshot** at an exact moment, **peek** at memory, drive the VICE **monitor** headless. One stdlib Python script, macOS/Linux/Windows |
| [`c64-kickassembler`](skills/c64-kickassembler/SKILL.md) | KickAssembler v5 syntax, the complete directive table, idioms (sine tables, PSID import), error messages and their fixes |
| [`c64-hardware`](skills/c64-hardware/SKILL.md) | register-level reference: memory map and banking, VIC-II, SID, CIAs, keyboard matrix, 6502 cycles and pitfalls |
| [`c64-demo-framework`](skills/c64-demo-framework/SKILL.md) | a tested skeleton for programs that take over the machine (NMI/RESTORE-proof, NTSC/PAL detection, frame loop, clean RUN/STOP exit), music tempo on NTSC, open borders, screen blanking |
| [`c64-code-review`](skills/c64-code-review/SKILL.md) | a hardware-correctness review against a fixed checklist, with STATIC / MEASURED / FOLLOW-UP modes |
| [`c64-vice-debugging`](skills/c64-vice-debugging/SKILL.md) | breakpoints conditioned on raster line and cycle, cycle stopwatch, profiler, CPU history, labels from your build; symptom → cause table |
| [`c64-disassembly`](skills/c64-disassembly/SKILL.md) | binary → KickAssembler source that rebuilds byte-identical, unpacking, separating code from data, Regenerator 2000's MCP server |

Plus [`agents/claude-code/c64-reviewer.md`](agents/claude-code/c64-reviewer.md), a Claude
Code subagent that runs the review in its own context.

### Included: the 6502-family skills by sunsided

The installers also set up the five `6502-*` skills from
**[sunsided/6502-skills](https://github.com/sunsided/6502-skills)**, included as a git
submodule in [`vendor/6502-skills`](vendor/6502-skills). They cover the CPU beyond the C64:

| Skill | What it adds |
|---|---|
| `6502-instruction-set` | 6502, 65C02 and 65816 opcodes, addressing modes, flags and cycle counts |
| `6502-memory-map` | memory maps, I/O and ROM entry points for the Apple II, Commodore 64 and Atari 400/800/XL/XE |
| `6502-merlin-assembler` | reading and writing Merlin assembler source (Apple II/IIgs, and Merlin 64/128 on Commodore) |
| `6502-sweet16` | Wozniak's SWEET16 16-bit interpreter |
| `6502-to-rust` | porting 6502 assembly to Rust |

They are sunsided's work, not part of this kit, and are not covered by this kit's license.
The submodule points at their repository instead of copying it, so credit and updates stay
with them. For C64 work the `c64-*` skills come first; the `6502-*` ones help with 65C02/65816
code and other 6502 machines.

**NTSC and PAL are both first-class.** Everything budgets against NTSC's 17095-cycle frame
unless the project says it is PAL-only, because code that fits only PAL's 19656 cycles is
broken for half the world's machines.

## Tools the skills call

The skills never call a tool by a hard-coded path. They go through one script,
`skills/c64-toolchain/scripts/c64.py`, which finds each tool (env var → saved config →
PATH → the usual install folders for your OS) and runs it the same way on every platform.

| Tool | Needed for | Used by skills |
|---|---|---|
| **Python 3.8+** | running `c64.py` (standard library only, nothing to `pip install`) | all |
| **Java 8+** | running KickAssembler | toolchain, kickassembler, code-review, demo-framework |
| **[KickAssembler](http://theweb.dk/KickAssembler)** (`KickAss.jar`) | `c64.py build` | toolchain, kickassembler, code-review, demo-framework, disassembly |
| **[VICE](https://vice-emu.sourceforge.io)** (`x64sc`, plus `c1541`, `petcat`) | `c64.py run / shot / peek / mon` | toolchain, vice-debugging, code-review (MEASURED), demo-framework, disassembly |
| [Regenerator 2000](https://github.com/ricardoquesada/regenerator2000) *(optional)* | disassembly, MCP server | disassembly |
| [Exomizer](https://bitbucket.org/magli143/exomizer) *(optional)* | crunching a release `.prg` | toolchain |

`c64.py doctor` lists what it found and prints the install command for anything missing on
your OS. Any path can be forced with an environment variable: `C64_JAVA`,
`C64_KICKASS_JAR`, `C64_X64SC`, `C64_C1541`, `C64_PETCAT`, `C64_REGENERATOR`,
`C64_EXOMIZER`. `C64_VIDEO=ntsc|pal` sets the default video standard.

## Setup on macOS

```sh
# 1. Tools
brew install --cask temurin                # Java
brew install vice                          # VICE: x64sc, c1541, petcat in /opt/homebrew/bin
#    (or the arm64 / x86_64 .dmg from vice-emu.sourceforge.io, e.g. into /Applications)
curl -LO http://theweb.dk/KickAssembler/KickAssembler.zip
sudo mkdir -p /Applications/KickAssembler && sudo unzip KickAssembler.zip -d /Applications/KickAssembler
brew install exomizer                      # optional
#    Regenerator 2000 (optional): download from its GitHub releases into /Applications/regenerator

# 2. Skills (symlinks: `git pull` updates them)
git clone --recurse-submodules https://github.com/todddube/c64-agent-kit ~/c64-agent-kit
~/c64-agent-kit/install.sh --claude --with-agent     # Claude Code
~/c64-agent-kit/install.sh --agents                  # Codex, Cursor, Copilot, Gemini CLI, opencode

# 3. Check
python3 ~/c64-agent-kit/skills/c64-toolchain/scripts/c64.py doctor --save
```
- A VICE `.dmg` downloaded by a browser may be blocked by Gatekeeper on first launch. Open
  it once from Finder (right-click → Open), or run `xattr -dr com.apple.quarantine
  /Applications/vice-*`. VICE agents launch from scripts have to start without that dialog.
- `doctor` finds VICE in `/Applications/vice*/bin`, `/opt/homebrew/bin` and
  `/usr/local/bin`, and KickAssembler in `/Applications/KickAssembler` or `~/KickAssembler`.

## Setup on Windows

In PowerShell:

```powershell
# 1. Tools
winget install Python.Python.3.13
winget install EclipseAdoptium.Temurin.21.JRE
winget install VICE-Team.VICE.GTK3
#    (or unzip GTK3VICE-*-win64.zip from vice-emu.sourceforge.io to C:\GTK3VICE-...)
Invoke-WebRequest http://theweb.dk/KickAssembler/KickAssembler.zip -OutFile KickAssembler.zip
Expand-Archive KickAssembler.zip C:\KickAssembler
#    Regenerator 2000 / Exomizer (optional): unzip their Windows releases, e.g. to C:\Tools

# 2. Skills (directory junctions: no admin rights or Developer Mode needed)
git clone --recurse-submodules https://github.com/todddube/c64-agent-kit $HOME\c64-agent-kit
& $HOME\c64-agent-kit\install.ps1 -Claude -WithAgent   # Claude Code
& $HOME\c64-agent-kit\install.ps1 -Agents              # Codex, Cursor, Copilot, Gemini CLI, opencode

# 3. Check
py -3 $HOME\c64-agent-kit\skills\c64-toolchain\scripts\c64.py doctor --save
```
- On Windows the Python command is `py -3` (or `python`), not `python3`. The skills say
  `python3`; agents on Windows should substitute `py -3`.
- If PowerShell refuses to run `install.ps1`, allow local scripts for this session:
  `Set-ExecutionPolicy -Scope Process Bypass`.
- `doctor` finds VICE under `C:\Program Files\GTK3VICE*`, `C:\GTK3VICE*`, `C:\SDL2VICE*`,
  `C:\Tools\GTK3VICE*`, `C:\Tools\VICE*`, your home folder and winget's package folder, in `bin\` (GTK3 builds)
  or the top folder (SDL2 builds). KickAssembler: `C:\KickAssembler`,
  `C:\Tools\KickAssembler`, `%USERPROFILE%\KickAssembler`. Anything else: set `C64_X64SC` /
  `C64_KICKASS_JAR`, or run `doctor --save` once the tools are on PATH.
- The config `doctor --save` writes lives in `%APPDATA%\c64-agent-kit\config.json`
  (macOS/Linux: `~/.config/c64-agent-kit/config.json`).

## Setup on Linux

`apt install default-jre vice` (Debian/Ubuntu ship VICE without the ROMs; add them from
the VICE source tarball), unzip KickAssembler to `~/KickAssembler`, then use `install.sh`
exactly as on macOS.

Already cloned without `--recurse-submodules`? Run `git submodule update --init` in the
checkout, then the installer again. To update everything later:
`git pull --recurse-submodules` (or `git submodule update --remote` for sunsided's latest).

## Other ways to install the skills

```sh
npx skills add todddube/c64-agent-kit     # any of 30+ agents, interactive picker (Node)
gh skill install todddube/c64-agent-kit   # GitHub CLI
./install.sh --project ~/code/mydemo      # one repo only (.claude/skills + .agents/skills)
.\install.ps1 -Project C:\code\mydemo     # same on Windows
```
`npx skills` and `gh skill` install the `c64-*` skills. Add the 6502 skills the same way
from their own repository: `npx skills add sunsided/6502-skills`.

Where each agent looks:

| Agent | Personal | Per project |
|---|---|---|
| Claude Code | `~/.claude/skills` | `.claude/skills` |
| OpenAI Codex | `~/.agents/skills` | `.agents/skills` |
| Cursor | `~/.agents/skills`, `~/.cursor/skills` (also reads `~/.claude/skills`) | `.agents/skills`, `.cursor/skills` |
| GitHub Copilot (CLI, VS Code agent mode, cloud agent) | `~/.agents/skills`, `~/.copilot/skills` | `.agents/skills`, `.github/skills`, `.claude/skills` |
| Gemini CLI | `~/.agents/skills`, `~/.gemini/skills` | `.agents/skills`, `.gemini/skills` |
| opencode | `~/.config/opencode/skills` | `.opencode/skills`, `.agents/skills` |

(`~` is `%USERPROFILE%` on Windows.) Cursor and Copilot read both the Claude and the
`.agents` locations. If you use them alongside Claude Code, install into one location
only, or each skill may be listed twice.

## Try it

Ask your agent things like:

- "Start a new C64 demo called starfield and show me a screenshot after one second."
- "Why is my raster split flickering on NTSC? Measure which line the IRQ ends on."
- "Review `intro.asm` for hardware bugs, STATIC mode."
- "Disassemble `oldgame.prg` into KickAssembler source that rebuilds identically."

## Development

```sh
python3 tests/smoke.py            # metadata + build + VICE (NTSC and PAL) + disassembly round trip
python3 tests/smoke.py --static   # metadata only
```
CI (GitHub Actions) runs the smoke test and both installers on Windows, macOS and Linux
with KickAssembler. The VICE and Regenerator checks need those tools and a display, so they
run locally only. They are verified on macOS (arm64).
See [AGENTS.md](AGENTS.md) for how the skills are written.

## License

MIT. See [LICENSE](LICENSE). This covers the kit's own files, not
`vendor/6502-skills`, which belongs to its author
([sunsided/6502-skills](https://github.com/sunsided/6502-skills)). KickAssembler, VICE and Regenerator 2000 are separate
projects under their own licenses; none of their code or manuals is included here.
