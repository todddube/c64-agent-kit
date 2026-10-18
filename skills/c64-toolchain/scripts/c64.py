#!/usr/bin/env python3
"""c64.py - find, build with and run the C64 toolchain from any AI coding agent.

One stdlib-only script so the same commands work in every agent and on
macOS, Linux and Windows:

    c64.py doctor [--save]                  find the tools, print what is missing
    c64.py build SRC.asm [--odir DIR] [--vicesymbols] [-- KICKASS-ARGS...]
    c64.py run PRG [--pal|--ntsc]           launch VICE detached (log: PRG-vice.log)
    c64.py shot PRG --seconds S --out F.png [--pal|--ntsc]
    c64.py peek PRG --seconds S [--mem START END]... [--shot F.png] [--pal|--ntsc]
    c64.py mon PRG --seconds S [--labels F.vs] -c CMD [-c CMD]... [--pal|--ntsc]

Tool paths come from, in order: environment variables (C64_JAVA,
C64_KICKASS_JAR, C64_X64SC, C64_C1541, C64_PETCAT, C64_REGENERATOR,
C64_EXOMIZER), the config file written by `doctor --save`, the PATH, then the
usual install locations for the platform. C64_VIDEO=ntsc|pal sets the default
video standard (ntsc: its 17095-cycle frame is the tighter budget).

`peek` is the measurement tool: it runs a .prg to an exact emulated time and
dumps memory and/or a screenshot, in about 10 s. It picks a free monitor port
per run and only ever kills the VICE it started, so several agents can use it
at once. Never `pkill x64sc` and never `sleep`-poll the emulator by hand.
"""
import argparse, glob, json, os, re, shutil, signal, socket, subprocess, sys, time

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
HZ = {"ntsc": 1022727, "pal": 985248}          # CPU clock, cycles per second
FRAME = {"ntsc": 17095, "pal": 19656}           # cycles per frame
DEFAULT_BOOT = 3200000                          # cycles VICE spends booting + autostarting
EXE = ".exe" if IS_WIN else ""

# KickAssembler noise on a successful build. What survives this filter is an
# error, a warning, or the source's own .print output.
NOISE = re.compile(r"^//|^parsing$|^flex pass|^Output pass$|^Output dir:|^$|"
                   r"^ +(Music:|init |\$)")


def mon_path(path):
    """A host path for a quoted VICE monitor argument. Forward slashes work on
    Windows too and avoid backslash escapes inside the monitor's strings."""
    return os.path.abspath(path).replace("\\", "/")


def config_path():
    if IS_WIN:
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(base, "c64-agent-kit", "config.json")


def load_config():
    try:
        with open(config_path()) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


CONFIG = load_config()


def first_file(patterns):
    for pat in patterns:
        for hit in sorted(glob.glob(os.path.expanduser(pat)), reverse=True):
            if os.path.isfile(hit):
                return hit
    return None


def vice_dirs():
    """Directories a VICE install keeps its command-line tools in."""
    if IS_MAC:
        return ["/Applications/vice*/bin", "/Applications/VICE*/bin",
                "~/Applications/vice*/bin", "/opt/homebrew/bin", "/usr/local/bin"]
    if IS_WIN:
        # GTK3 builds keep the .exe files in bin\, SDL2 builds in the top folder;
        # winget unpacks under %LOCALAPPDATA%\Microsoft\WinGet\Packages.
        winget = os.path.join(os.environ.get("LOCALAPPDATA", r"~\AppData\Local"),
                              "Microsoft", "WinGet", "Packages", "VICE-Team.VICE*")
        roots = [r"C:\Program Files\GTK3VICE*", r"C:\Program Files\SDL2VICE*",
                 r"C:\Program Files\VICE*", r"C:\GTK3VICE*", r"C:\SDL2VICE*", r"C:\VICE*",
                 r"C:\Tools\GTK3VICE*", r"C:\Tools\VICE*", r"~\GTK3VICE*", r"~\SDL2VICE*",
                 os.path.join(winget, "*")]
        return [d for r in roots for d in (os.path.join(r, "bin"), r)]
    return ["/usr/bin", "/usr/local/bin", "/opt/vice*/bin", "~/vice*/bin"]


def vice_tool(name):
    hit = shutil.which(name)
    if hit:
        return hit
    found = first_file(os.path.join(d, name + EXE) for d in vice_dirs())
    if found:
        return found
    if IS_MAC:  # app-bundle-only installs
        return first_file([f"/Applications/vice*/{name}.app/Contents/MacOS/{name}",
                           f"/Applications/VICE*/{name}.app/Contents/MacOS/{name}"])
    return None


def locate(key):
    """Path of tool `key`, or None."""
    env = os.environ.get("C64_" + key.upper())
    if env:
        return env
    if CONFIG.get(key) and os.path.exists(CONFIG[key]):
        return CONFIG[key]
    if key == "java":
        return shutil.which("java")
    if key == "kickass_jar":
        return first_file([
            "/Applications/KickAssembler/KickAss.jar", "~/Applications/KickAssembler/KickAss.jar",
            "~/KickAssembler/KickAss.jar", "~/kickassembler/KickAss.jar",
            "/opt/KickAssembler/KickAss.jar", "/opt/kickassembler/KickAss.jar",
            "/usr/local/share/kickassembler/KickAss.jar", "/usr/share/kickassembler/KickAss.jar",
            r"C:\KickAssembler\KickAss.jar", r"C:\Program Files\KickAssembler\KickAss.jar",
            r"C:\Tools\KickAssembler\KickAss.jar", r"~\KickAssembler\KickAss.jar"])
    if key in ("x64sc", "c1541", "petcat"):
        return vice_tool(key)
    if key == "regenerator":
        return shutil.which("regenerator2000") or first_file([
            "/Applications/regenerator/regenerator2000", "/Applications/regenerator2000",
            "~/regenerator/regenerator2000", "/opt/regenerator/regenerator2000",
            r"C:\regenerator\regenerator2000.exe", r"C:\Tools\regenerator\regenerator2000.exe",
            r"~\regenerator\regenerator2000.exe"])
    if key == "exomizer":
        return shutil.which("exomizer")
    return None


def need(key, why):
    path = locate(key)
    if not path:
        sys.exit(f"c64.py: {key} not found ({why}). Run `c64.py doctor` for install hints, "
                 f"or set C64_{key.upper()}.")
    return path


def video(args):
    if getattr(args, "pal", False):
        return "pal"
    if getattr(args, "ntsc", False):
        return "ntsc"
    std = os.environ.get("C64_VIDEO", CONFIG.get("video", "ntsc")).lower()
    return std if std in HZ else "ntsc"


# --- doctor -----------------------------------------------------------------

if IS_MAC:
    HINT = {"java": "brew install --cask temurin",
            "kickass_jar": "unzip theweb.dk/KickAssembler/KickAssembler.zip to /Applications/KickAssembler",
            "x64sc": "brew install vice  (or the arm64/x86_64 .dmg from vice-emu.sourceforge.io)",
            "regenerator": "github.com/ricardoquesada/regenerator2000 releases",
            "exomizer": "brew install exomizer"}
elif IS_WIN:
    HINT = {"java": "winget install EclipseAdoptium.Temurin.21.JRE",
            "kickass_jar": r"unzip theweb.dk/KickAssembler/KickAssembler.zip to C:\KickAssembler",
            "x64sc": r"winget install VICE-Team.VICE.GTK3  (or unzip GTK3VICE-*-win64.zip to C:\)",
            "regenerator": "github.com/ricardoquesada/regenerator2000 releases (regenerator2000.exe)",
            "exomizer": "bitbucket.org/magli143/exomizer (win32 build in the release zip)"}
else:
    HINT = {"java": "apt install default-jre  (or your distro's JRE)",
            "kickass_jar": "unzip theweb.dk/KickAssembler/KickAssembler.zip to ~/KickAssembler",
            "x64sc": "apt install vice  (then add the ROMs if your distro omits them)",
            "regenerator": "github.com/ricardoquesada/regenerator2000 releases",
            "exomizer": "build from bitbucket.org/magli143/exomizer"}
HINT["c1541"] = HINT["petcat"] = "ships with VICE (same folder as x64sc)"

TOOLS = [("java", True), ("kickass_jar", True), ("x64sc", True), ("c1541", False),
         ("petcat", False), ("regenerator", False), ("exomizer", False)]


def cmd_doctor(a):
    found, missing_required = {}, False
    print(f"config: {config_path()}{'' if CONFIG else ' (none yet)'}")
    for key, required in TOOLS:
        path = locate(key)
        mark = "ok " if path else ("MISSING" if required else "-- ")
        print(f"  {mark:7} {key:12} {path or 'install: ' + HINT[key]}")
        if path:
            found[key] = path
        elif required:
            missing_required = True
    if found.get("java"):
        try:
            out = subprocess.run([found["java"], "-version"], capture_output=True, text=True)
            print("  java: " + (out.stderr or out.stdout).splitlines()[0])
        except (OSError, IndexError):
            print("  java: present but `java -version` failed")
    print(f"  video default: {video(a)} (C64_VIDEO=ntsc|pal)")
    if a.save:
        found["video"] = video(a)
        os.makedirs(os.path.dirname(config_path()), exist_ok=True)
        with open(config_path(), "w") as f:
            json.dump(found, f, indent=2)
        print(f"saved {config_path()}")
    sys.exit(1 if missing_required else 0)


# --- build ------------------------------------------------------------------

def cmd_build(a):
    java = need("java", "KickAssembler is a Java program")
    jar = need("kickass_jar", "the assembler")
    src = os.path.abspath(a.src)
    if not os.path.isfile(src):
        sys.exit(f"c64.py: no such source file: {a.src}")
    odir = os.path.abspath(a.odir or os.path.join(os.path.dirname(src), "bin"))
    os.makedirs(odir, exist_ok=True)
    cmd = [java, "-jar", jar, src, "-odir", odir]
    if a.vicesymbols:
        cmd.append("-vicesymbols")
    cmd += a.extra
    # KickAssembler resolves #import relative to the source; run from its directory.
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=os.path.dirname(src))
    out = proc.stdout + proc.stderr
    with open(os.path.join(odir, "buildlog.txt"), "w", encoding="utf-8") as f:
        f.write(out)
    shown = [l for l in out.splitlines() if not NOISE.search(l)]
    print("\n".join(shown))
    failed = proc.returncode != 0 or any(l.lstrip().startswith("Error") for l in shown) \
        or not any(l.startswith("Writing") for l in shown)
    if failed:
        print(f"BUILD FAILED (full log: {os.path.join(odir, 'buildlog.txt')})")
        sys.exit(1)


# --- running VICE -----------------------------------------------------------

def spawn(cmd, log):
    kw = {"stdout": log, "stderr": subprocess.STDOUT}
    if IS_WIN:
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True   # own process group: killable as a unit
    return subprocess.Popen(cmd, **kw)


def kill_tree(proc):
    # On some installs x64sc is a launcher script that starts the real
    # emulator as a child, so kill the whole group, never just the pid -
    # and never by name, because other agents may be running VICE too.
    try:
        if IS_WIN:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass


def check_prg(path):
    if not os.path.isfile(path):
        sys.exit(f"c64.py: no such file: {path}")
    return os.path.abspath(path)


def cmd_run(a):
    x64sc = need("x64sc", "the VICE C64 emulator")
    prg = check_prg(a.prg)
    std = video(a)
    log_path = prg + "-vice.log"
    log = open(log_path, "w")
    proc = spawn([x64sc, "-" + std, "-autostart", prg], log)
    print(f"VICE ({std}) pid {proc.pid}, log {log_path}")
    print("The log's 'Unknown disk image' / 'no CRT header' lines are autodetect probes; "
          "look for 'AUTOSTART: Loading PRG file'.")


def target_cycle(a, std):
    return a.boot + int(a.seconds * HZ[std])


def cmd_shot(a):
    x64sc = need("x64sc", "the VICE C64 emulator")
    prg, std = check_prg(a.prg), video(a)
    target = target_cycle(a, std)
    subprocess.run([x64sc, "-" + std, "-warp", "-limitcycles", str(target),
                    "-exitscreenshot", os.path.abspath(a.out), "-autostart", prg],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.isfile(a.out):
        sys.exit("c64.py: VICE exited without writing the screenshot")
    print(f"{std} cycle {target} (~{a.seconds:g} s after boot): {a.out}")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Monitor:
    """Minimal client for VICE's text remote monitor."""

    def __init__(self, port):
        self.sock = None
        for _ in range(200):
            try:
                self.sock = socket.create_connection(("127.0.0.1", port), timeout=1)
                break
            except OSError:
                time.sleep(0.05)
        if self.sock is None:
            sys.exit("c64.py: could not reach the VICE remote monitor")
        self.sock.settimeout(30)
        self.buf = b""

    def drain(self):
        """Discard output nobody asked for (the prompt VICE prints on break-in)."""
        self.sock.settimeout(0.15)
        try:
            while self.sock.recv(65536):
                pass
        except (socket.timeout, BlockingIOError):
            pass
        self.sock.settimeout(30)
        self.buf = b""

    def send(self, line):
        self.sock.sendall((line + "\n").encode())

    def ask(self, line, marker):
        """Send a command; read until `marker` has arrived and a prompt follows.
        Breaking into a running machine emits a bare prompt first, which the
        marker skips."""
        self.drain()
        self.send(line)
        while True:
            k = self.buf.find(marker)
            if k >= 0:
                m = re.search(rb"\(C:\$[0-9a-f]{4}\) ", self.buf[k:])
                if m:
                    return self.buf[:k + m.end()].decode(errors="replace")
            data = self.sock.recv(65536)
            if not data:
                return self.buf.decode(errors="replace")
            self.buf += data

    def clock(self):
        """Break in (if running) and return the CPU stopwatch, in cycles."""
        out = self.ask("r", b".;")
        m = re.search(r"^\.;[0-9a-f]{4} .*?(\d+)\s*$", out, re.M)
        return int(m.group(1))


def start_monitored(a):
    """Start VICE with a remote monitor on a free port and run it (in warp) to
    the target emulated time. Returns (proc, monitor, video standard, cycle)."""
    x64sc = need("x64sc", "the VICE C64 emulator")
    prg, std = check_prg(a.prg), video(a)
    target = target_cycle(a, std)
    port = free_port()
    proc = spawn([x64sc, "-" + std, "-warp", "-remotemonitor",
                  "-remotemonitoraddress", f"ip4://127.0.0.1:{port}", "-autostart", prg],
                 subprocess.DEVNULL)
    try:
        mon = Monitor(port)
        warp = True
        while True:
            clk = mon.clock()
            if clk >= target:
                break
            if warp and target - clk < 3000000:
                mon.ask("warp off", b"")
                warp = False
            mon.send("x")               # resume; the next command breaks in
            # sleep most of the remaining distance (warp speed varies with the
            # host; 40M cycles/s is an upper bound), then check again
            rate = 40e6 if warp else 1.2e6
            time.sleep(min(0.5, max(0.01, (target - clk) / rate)))
        if warp:
            mon.ask("warp off", b"")
    except BaseException:
        kill_tree(proc)
        raise
    print(f"{std} cycle {clk} (target {target}, +{(clk - target) / HZ[std] * 1000:.0f} ms)")
    return proc, mon, std, clk


def cmd_peek(a):
    if not a.mem:
        if not a.shot:
            sys.exit("c64.py peek: nothing to do (give --mem and/or --shot)")
        a.out = a.shot
        return cmd_shot(a)            # screenshot only: -limitcycles is exact
    proc, mon, std, clk = start_monitored(a)
    try:
        for start, end in a.mem:
            out = mon.ask(f"m {start} {end}", b">C:")
            print("\n".join(l[l.index(">C:"):] for l in out.splitlines() if ">C:" in l))
        if a.shot:
            mon.ask(f'screenshot "{mon_path(a.shot)}" 2', b"")
            print(f"screenshot {a.shot}")
    finally:
        kill_tree(proc)


PROMPT = re.compile(rb"\(C:\$[0-9a-f]{4}\) \Z")


def cmd_mon(a):
    """Run monitor commands at an exact emulated time, headless. `x`/`g`
    resume the machine and wait (up to --timeout wall seconds) for the next
    checkpoint to stop it, printing what VICE reports."""
    proc, mon, std, clk = start_monitored(a)
    try:
        cmds = list(a.cmd)
        if a.labels:
            cmds.insert(0, f'll "{mon_path(a.labels)}"')
        for c in cmds:
            print(f"> {c}")
            mon.drain()
            mon.send(c)
            resumes = c.split()[0] in ("x", "exit", "g", "goto", "un", "until", "ret", "return")
            wait = a.timeout if resumes else 5
            buf, deadline = b"", time.time() + wait
            mon.sock.settimeout(0.2)
            while time.time() < deadline and not PROMPT.search(buf):
                try:
                    data = mon.sock.recv(65536)
                except socket.timeout:
                    continue
                if not data:
                    break
                buf += data
            mon.sock.settimeout(30)
            text = PROMPT.sub(b"", buf).decode(errors="replace").strip("\n")
            if resumes and not PROMPT.search(buf):
                text += f"\n(no checkpoint hit within {wait:g} s; breaking in)"
                mon.ask("r", b".;")
            if text:
                print(text)
    finally:
        kill_tree(proc)


def main():
    # Monitor dumps include PETSCII bytes; never let a Windows console code page
    # turn them into a crash.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("doctor", help="find the tools and report what is missing")
    p.add_argument("--save", action="store_true", help="write found paths to the config file")
    p.set_defaults(fn=cmd_doctor)

    p = sub.add_parser("build", help="assemble with KickAssembler, print only what matters")
    p.add_argument("src")
    p.add_argument("--odir", help="output directory (default: bin/ beside the source)")
    p.add_argument("--vicesymbols", action="store_true",
                   help="also write a .vs label file for the VICE monitor (`ll`)")
    p.set_defaults(fn=cmd_build)

    def std_flags(p):
        g = p.add_mutually_exclusive_group()
        g.add_argument("--pal", action="store_true")
        g.add_argument("--ntsc", action="store_true")

    def time_flags(p):
        p.add_argument("--seconds", type=float, required=True,
                       help="emulated seconds after the program starts")
        p.add_argument("--boot", type=int, default=DEFAULT_BOOT,
                       help=f"cycles spent booting + autostarting (default {DEFAULT_BOOT})")

    p = sub.add_parser("run", help="launch VICE detached with autostart")
    p.add_argument("prg"); std_flags(p)
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("shot", help="screenshot at an exact emulated time")
    p.add_argument("prg"); p.add_argument("--out", required=True)
    std_flags(p); time_flags(p)
    p.set_defaults(fn=cmd_shot)

    p = sub.add_parser("peek", help="dump memory (and/or screenshot) at an exact emulated time")
    p.add_argument("prg")
    p.add_argument("--mem", nargs=2, action="append", default=[], metavar=("START", "END"),
                   help="hex range, e.g. --mem c000 c03f (repeatable)")
    p.add_argument("--shot")
    std_flags(p); time_flags(p)
    p.set_defaults(fn=cmd_peek)

    p = sub.add_parser("mon", help="run VICE monitor commands at an exact emulated time")
    p.add_argument("prg")
    p.add_argument("-c", "--cmd", action="append", default=[], required=True,
                   help='monitor command, repeatable, in order (e.g. -c "break exec .irq" -c x -c r)')
    p.add_argument("--labels", help="KickAssembler .vs label file (build --vicesymbols) to load first")
    p.add_argument("--timeout", type=float, default=10,
                   help="wall seconds to wait for a checkpoint after x/g/until (default 10)")
    std_flags(p); time_flags(p)
    p.set_defaults(fn=cmd_mon)

    # Everything after a bare -- goes straight to KickAssembler (build only).
    argv = sys.argv[1:]
    extra = []
    if "--" in argv:
        k = argv.index("--")
        argv, extra = argv[:k], argv[k + 1:]
    a = ap.parse_args(argv)
    a.extra = extra
    a.fn(a)


if __name__ == "__main__":
    main()
