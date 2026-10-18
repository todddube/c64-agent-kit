# Working on c64-agent-kit

This repo *is* a set of Agent Skills; there is no application code besides
`skills/c64-toolchain/scripts/c64.py` and `install.sh`.

## Layout

- `skills/<name>/SKILL.md`: one skill per folder. Frontmatter has only `name` (equals the
  folder name; lowercase, hyphens, ≤ 64 chars) and `description` (≤ 1024 chars, says
  *what* and *when to use it*, with trigger phrases). Nothing agent-specific in the
  frontmatter, so every agent can read it.
- `skills/<name>/references/`, `templates/`, `scripts/`: loaded on demand. Keep `SKILL.md`
  short and point to these by relative path.
- A skill refers to another as "the `c64-xyz` skill", never by an absolute path: users
  install them in different places.
- `agents/claude-code/`: optional subagent wrappers. They only point at a skill; the
  content lives in the skill.

## Rules for content

- **Verified, not recalled.** Register facts come from the references; tool flags and
  monitor commands are checked against the tool's own `--help`/`help`. Anything that
  claims "tested" must be covered by `tests/smoke.py`.
- **Both video standards.** Default to NTSC budgets (17095 cycles/frame), always give PAL
  (19656) too, and never write a raster wait above line `$106`.
- **No tool paths in skills.** Go through `c64.py`, which finds tools via env vars,
  config, PATH and platform defaults.
- `c64.py` stays a single stdlib-only file that runs on macOS, Linux and Windows.
- Agents running in parallel share the machine: never `pkill x64sc`, never a fixed monitor
  port, never `sleep`-poll the emulator.
- Don't vendor third-party manuals or skills without a license that allows it.

## Before committing

```sh
python3 tests/smoke.py
bash -n install.sh
```
