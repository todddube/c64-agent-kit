#!/usr/bin/env bash
# install.sh - install the c64-agent-kit skills for your AI coding agent(s).
#
# Most agents read the open Agent Skills layout from .agents/skills (Codex, Cursor,
# GitHub Copilot, Gemini CLI, opencode, ...). Claude Code reads .claude/skills.
#
#   ./install.sh --claude                 # Claude Code, personal   -> ~/.claude/skills
#   ./install.sh --agents                 # Codex/Cursor/Copilot/Gemini/opencode -> ~/.agents/skills
#   ./install.sh --project DIR            # one repo: DIR/.claude/skills + DIR/.agents/skills
#   ./install.sh --claude --with-agent    # also the Claude Code c64-reviewer subagent
#   ./install.sh --agents --copy          # copy instead of symlink
#   ./install.sh --claude --agents --uninstall
#
# Symlinks (the default) keep every install pointing at this checkout, so
# `git pull` here updates them all. Use --copy on Windows or to vendor the
# skills into a repository.
#
# Cursor and Copilot read BOTH ~/.claude/skills and ~/.agents/skills. If you use one
# of them alongside Claude Code, installing into both locations can list each skill
# twice; --claude alone covers Claude Code + Cursor + Copilot.
set -euo pipefail

KIT="$(cd "$(dirname "$0")" && pwd)"
targets=() agent_dirs=() mode=link action=install with_agent=0

usage() { sed -n '2,21p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --claude)    targets+=("$HOME/.claude/skills"); agent_dirs+=("$HOME/.claude/agents") ;;
    --agents)    targets+=("$HOME/.agents/skills") ;;
    --project)   [ $# -ge 2 ] || usage 1
                 d="$(cd "$2" && pwd)"; shift
                 targets+=("$d/.claude/skills" "$d/.agents/skills")
                 agent_dirs+=("$d/.claude/agents") ;;
    --to)        [ $# -ge 2 ] || usage 1; targets+=("$2"); shift ;;
    --copy)      mode=copy ;;
    --with-agent) with_agent=1 ;;
    --uninstall) action=uninstall ;;
    -h|--help)   usage 0 ;;
    *)           echo "unknown option: $1" >&2; usage 1 ;;
  esac
  shift
done
[ ${#targets[@]} -gt 0 ] || usage 1

skills=()
for s in "$KIT"/skills/*/; do [ -f "$s/SKILL.md" ] && skills+=("$(basename "$s")"); done

place() {   # place SRC DEST
  local src="$1" dest="$2"
  if [ -L "$dest" ]; then rm "$dest"
  elif [ -e "$dest" ]; then
    echo "  skip $dest: exists and is not a symlink from this kit (remove it first)" >&2
    return
  fi
  if [ "$mode" = copy ]; then cp -R "$src" "$dest"; else ln -s "$src" "$dest"; fi
  echo "  $dest"
}

remove() {  # remove DEST OURFILE THEIRFILE - only what this kit installed
  local dest="$1" ours="$2" theirs="$3"
  if [ -L "$dest" ]; then
    case "$(readlink "$dest")" in "$KIT"/*) rm "$dest"; echo "  removed $dest" ;;
      *) echo "  skip $dest: symlink to somewhere else" >&2 ;; esac
  elif [ -e "$dest" ]; then
    if cmp -s "$ours" "$theirs"; then rm -rf "$dest"; echo "  removed $dest (copy)"
    else echo "  skip $dest: differs from this kit's version (edited?) - remove by hand" >&2; fi
  fi
}

for t in "${targets[@]}"; do
  echo "$action -> $t"
  [ "$action" = install ] && mkdir -p "$t"
  for s in "${skills[@]}"; do
    if [ "$action" = uninstall ]; then
      remove "$t/$s" "$KIT/skills/$s/SKILL.md" "$t/$s/SKILL.md"
    else
      place "$KIT/skills/$s" "$t/$s"
    fi
  done
done

if [ "$with_agent" = 1 ] || [ "$action" = uninstall ]; then
  for d in "${agent_dirs[@]+"${agent_dirs[@]}"}"; do
    if [ "$action" = uninstall ]; then
      remove "$d/c64-reviewer.md" "$KIT/agents/claude-code/c64-reviewer.md" "$d/c64-reviewer.md"
    else
      mkdir -p "$d"
      place "$KIT/agents/claude-code/c64-reviewer.md" "$d/c64-reviewer.md"
    fi
  done
fi

[ "$action" = install ] && echo "Done. Next: python3 \"$KIT/skills/c64-toolchain/scripts/c64.py\" doctor"
exit 0
