#!/usr/bin/env python3
"""Smoke test for the kit: skill metadata, toolchain, emulator, disassembler.

    python3 tests/smoke.py            # everything the installed tools allow
    python3 tests/smoke.py --static   # metadata only (no Java/VICE needed, e.g. CI)

Every check that needs a tool is skipped, not failed, when `c64.py doctor`
cannot find that tool.
"""
import json, os, re, subprocess, sys, tempfile

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C64 = os.path.join(KIT, "skills", "c64-toolchain", "scripts", "c64.py")
TEMPLATE = os.path.join(KIT, "skills", "c64-demo-framework", "templates", "main.asm")
sys.path.insert(0, os.path.dirname(C64))
import c64  # noqa: E402

failures = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'  - ' + detail if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def skip(name, why):
    print(f"skip  {name}  ({why})")


def run(*args):
    p = subprocess.run([sys.executable, C64, *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def test_metadata():
    skills_dir = os.path.join(KIT, "skills")
    for name in sorted(os.listdir(skills_dir)):
        path = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8").read()
        m = re.match(r"---\n(.*?)\n---\n", text, re.S)
        check(f"{name}: frontmatter", bool(m))
        if not m:
            continue
        fields = dict(re.findall(r"^(\w[\w-]*):\s*(.*)$", m.group(1), re.M))
        raw_desc = fields.get("description", "")
        # A plain (unquoted) YAML scalar ends at " #" (a comment) and may not
        # contain ": ". Agents would silently see a truncated description.
        quoted = raw_desc.startswith('"') and raw_desc.endswith('"')
        check(f"{name}: description is YAML-safe",
              quoted or (" #" not in raw_desc and ": " not in raw_desc), raw_desc[:60])
        if quoted:
            fields["description"] = json.loads(raw_desc)
        check(f"{name}: name matches directory", fields.get("name") == name, fields.get("name", ""))
        check(f"{name}: name format", re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name or "") is not None
              and len(name) <= 64)
        desc = fields.get("description", "")
        check(f"{name}: description 1..1024 chars", 0 < len(desc) <= 1024, f"{len(desc)} chars")
        for ref in re.findall(r"`((?:references|templates|scripts)/[\w./-]+)`", text):
            check(f"{name}: {ref} exists", os.path.exists(os.path.join(KIT, "skills", name, ref)))


def test_vendor():
    """The 6502-* skills from the vendor/6502-skills submodule (not ours to lint)."""
    vendor = os.path.join(KIT, "vendor", "6502-skills")
    if not os.path.isfile(os.path.join(vendor, "6502-instruction-set", "SKILL.md")):
        return skip("6502-* skills", "submodule not checked out: git submodule update --init")
    names = [n for n in sorted(os.listdir(vendor)) if os.path.isfile(os.path.join(vendor, n, "SKILL.md"))]
    for name in names:
        text = open(os.path.join(vendor, name, "SKILL.md"), encoding="utf-8").read()
        m = re.match(r"---\n(.*?)\n---\n", text, re.S)
        check(f"{name}: frontmatter names its folder",
              bool(m) and re.search(rf"^name:\s*{re.escape(name)}\s*$", m.group(1), re.M) is not None)
        check(f"{name}: no clash with a kit skill", not os.path.exists(os.path.join(KIT, "skills", name)))


def test_toolchain(tmp):
    if not (c64.locate("java") and c64.locate("kickass_jar")):
        return skip("build", "java or KickAss.jar not found")
    rc, out = run("build", TEMPLATE, "--odir", tmp, "--vicesymbols")
    check("template builds clean", rc == 0 and out.strip().splitlines()[0] == "Writing prg file: main.prg", out)
    bad = os.path.join(tmp, "bad.asm")
    open(bad, "w").write("BasicUpstart2(m)\nm: bne nowhere\n")
    rc, out = run("build", bad, "--odir", tmp)
    check("broken source fails with the error shown", rc != 0 and "Unknown symbol" in out, out)

    prg = os.path.join(tmp, "main.prg")
    if not c64.locate("x64sc"):
        return skip("emulator", "x64sc not found")
    for std, flag, frame in (("NTSC", "--ntsc", 17095), ("PAL", "--pal", 19656)):
        rc, out = run("peek", prg, "--seconds", "1", flag, "--mem", "0002", "0002", "--mem", "0400", "0403")
        want = "01" if std == "NTSC" else "00"
        check(f"{std}: template detects the standard", rc == 0 and f">C:0002  {want}" in out, out)
        rc, out = run("mon", prg, "--seconds", "1", flag, "--labels", os.path.join(tmp, "main.vs"),
                      "-c", "break exec .main_loop", "-c", "x", "-c", "sw reset", "-c", "x", "-c", "sw")
        m = re.search(r"Stopwatch:\s+(\d+)", out)
        # wait_frame polls $d012 in a 7-cycle loop (cmp abs + bne), so one pass
        # can land up to 7 cycles either side of the true frame length.
        check(f"{std}: one main-loop pass = one frame ({frame} cycles, +-7)",
              rc == 0 and m and abs(int(m.group(1)) - frame) <= 7, out[-400:])
    shot = os.path.join(tmp, "shot.png")
    rc, out = run("shot", prg, "--seconds", "1", "--out", shot)
    check("screenshot written", rc == 0 and os.path.getsize(shot) > 0, out)

    regen = c64.locate("regenerator")
    if not regen:
        return skip("disassembly round trip", "regenerator2000 not found")
    asm = os.path.join(tmp, "round.asm")
    subprocess.run([regen, prg, "--export_asm", asm, "--assembler", "kick"],
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=60)
    rc, out = run("build", asm, "--odir", os.path.join(tmp, "round"))
    same = rc == 0 and open(os.path.join(tmp, "round", "round.prg"), "rb").read() == open(prg, "rb").read()
    check("Regenerator export reassembles byte-identical", same, out)


def main():
    test_metadata()
    test_vendor()
    if "--static" not in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            test_toolchain(tmp)
    print(f"\n{len(failures)} failure(s)" if failures else "\nall passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
