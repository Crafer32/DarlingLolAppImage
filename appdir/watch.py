#!/usr/bin/env python3
"""Shut Darling down once the Riot Client and League are closed.

Darling keeps running while any Mac process is alive, and the Riot Client leaves background
agents behind (RiotClientServices, crash handlers) just like on a real Mac, so closing the
windows never stops darlingserver. This watcher looks at the guest processes (host processes
whose executable is Darling's mldr) and, when none of the visible apps has been running for
RCLOL_AUTO_SHUTDOWN_DELAY seconds, runs `darling shutdown` and then kills whatever is left.

Disable with RCLOL_AUTO_SHUTDOWN=0.
"""
import os
import re
import signal
import subprocess
import sys
import time

DPREFIX = os.environ["DPREFIX"]
MLDR = os.environ["DARLING_LOL_MLDR"]          # host path of the runtime's mldr
DARLING = os.environ["DARLING_LOL_DARLING"]    # our `darling` wrapper
DELAY = int(os.environ.get("RCLOL_AUTO_SHUTDOWN_DELAY", "90"))
STARTUP_LIMIT = 15 * 60   # give up waiting for the first window after this
POLL = 5

# processes that mean "the user still has something open"
VISIBLE = re.compile(
    r"Riot Client\.app/Contents/MacOS/Riot Client( |$)"
    r"|/MacOS/LeagueClient(Ux)?( |$)"
    r"|LeagueofLegends\.app/Contents/MacOS/LeagueofLegends"
    r"|LeagueOfLegends\.app/Contents/MacOS/"
    r"|/MacOS/Blitz( |$)"
    r"|Riot Client Installer|RiotClientInstaller"
)


def log(msg):
    print(f"darling-lol watch: {msg}", file=sys.stderr, flush=True)


def guest_processes():
    """(pid, cmdline) of every process running under this Darling runtime."""
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            exe = os.readlink(f"/proc/{pid}/exe")
            if exe.replace(" (deleted)", "") != MLDR:
                continue
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode(errors="replace")
            yield int(pid), cmd
        except OSError:
            continue


def darlingserver_pids():
    pids = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                args = f.read().split(b"\0")
            if args and args[0].endswith(b"darlingserver") and len(args) > 1 and args[1].decode() == DPREFIX:
                pids.append(int(pid))
        except OSError:
            continue
    return pids


def shutdown():
    log("no Riot/League window left: shutting Darling down")
    try:
        subprocess.run([DARLING, "shutdown"], timeout=30, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        pass
    for _ in range(20):
        if not darlingserver_pids() and not any(True for _ in guest_processes()):
            return
        time.sleep(1)
    # darling shutdown didn't finish (or left orphans): stop the guests, then the server
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for pid, _ in guest_processes():
            try:
                os.kill(pid, sig)
            except OSError:
                pass
        for pid in darlingserver_pids():
            try:
                os.kill(pid, sig)
            except OSError:
                pass
        time.sleep(3)
    log("Darling stopped" if not darlingserver_pids() else "darlingserver is still running")


def main():
    if os.environ.get("RCLOL_AUTO_SHUTDOWN", "1") == "0":
        return
    started = time.monotonic()
    seen = False
    last_visible = time.monotonic()
    while True:
        time.sleep(POLL)
        if not darlingserver_pids():
            if seen or time.monotonic() - started > 120:
                return          # Darling already stopped (by the user or the launcher)
            continue
        now = time.monotonic()
        if any(VISIBLE.search(cmd) for _, cmd in guest_processes()):
            seen = True
            last_visible = now
        elif seen and now - last_visible >= DELAY:
            shutdown()
            return
        elif not seen and now - started >= STARTUP_LIMIT:
            log("the Riot Client never opened")
            shutdown()
            return


if __name__ == "__main__":
    main()
