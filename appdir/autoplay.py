#!/usr/bin/env python3
"""Open League as soon as the Riot Client is signed in, without pressing Play.

The launcher already starts the Riot Client with --launch-product=league_of_legends, but under
Darling it stops at the Play button. Once the client is up and signed in ("Stay signed in"),
this asks the client's own local API to launch League, which is the request the Play button
sends. It does it once per session: closing League and going back to the Riot Client leaves the
client alone.

While League runs, the Riot Client window is minimized and taken off the taskbar, and it comes
back when League closes (RCLOL_HIDE_RIOT_CLIENT=0 leaves it alone).

Disable the launch with RCLOL_AUTOPLAY=0. Log in ~/.darling-lol/autoplay.log.
"""
import base64
import ctypes
import ctypes.util
import glob
import http.client
import json
import os
import re
import ssl
import sys
import time

DPREFIX = os.environ["DPREFIX"]
MLDR = os.environ["DARLING_LOL_MLDR"]
PATCHLINE = os.environ.get("RCLOL_LAUNCH_PATCHLINE", "live")
GIVE_UP = 15 * 60       # the user may take a while to sign in or the client may be patching
POLL = 3
LEAGUE = re.compile(r"/MacOS/LeagueClient(Ux)?( |$)|LeagueofLegends\.app/Contents/MacOS/")


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} darling-lol autoplay: {msg}", file=sys.stderr, flush=True)


def league_running():
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            if os.readlink(f"/proc/{pid}/exe").replace(" (deleted)", "") != MLDR:
                continue
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                if LEAGUE.search(f.read().replace(b"\0", b" ").decode(errors="replace")):
                    return True
        except OSError:
            continue
    return False


def lockfile():
    """(port, password) from the Riot Client's lockfile, or None while it isn't running."""
    for path in glob.glob(os.path.join(DPREFIX, "Users/*/Library/Application Support/Riot Games/Riot Client/Config/lockfile")):
        try:
            name, pid, port, password, proto = open(path).read().strip().split(":")
            return int(port), password
        except (OSError, ValueError):
            continue
    return None


def request(port, password, method, path):
    """(status, body) from the local API. http.client speaks HTTP/1.1, which the client needs."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE   # the client serves a self-signed certificate on 127.0.0.1
    conn = http.client.HTTPSConnection("127.0.0.1", port, context=ctx, timeout=10)
    auth = base64.b64encode(f"riot:{password}".encode()).decode()
    try:
        conn.request(method, path, headers={"Authorization": f"Basic {auth}", "Content-Length": "0"})
        r = conn.getresponse()
        return r.status, r.read().decode(errors="replace")
    finally:
        conn.close()


class Taskbar:
    """Hide or show the Riot Client's windows through the window manager (EWMH), with Xlib."""

    class ClientMessage(ctypes.Structure):
        _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong), ("send_event", ctypes.c_int),
                    ("display", ctypes.c_void_p), ("window", ctypes.c_ulong), ("message_type", ctypes.c_ulong),
                    ("format", ctypes.c_int), ("data", ctypes.c_long * 5)]

    class XEvent(ctypes.Union):
        pass

    class ClassHint(ctypes.Structure):
        _fields_ = [("res_name", ctypes.c_void_p), ("res_class", ctypes.c_void_p)]

    XEvent._fields_ = [("xclient", ClientMessage), ("pad", ctypes.c_long * 24)]

    def __init__(self):
        self.x = ctypes.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
        x = self.x
        x.XOpenDisplay.restype = ctypes.c_void_p
        x.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x.XDefaultRootWindow.restype = ctypes.c_ulong
        x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        x.XInternAtom.restype = ctypes.c_ulong
        x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x.XGetWindowProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_long, ctypes.c_long,
                                         ctypes.c_int, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
                                         ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_ulong),
                                         ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_void_p)]
        x.XGetClassHint.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(self.ClassHint)]
        x.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.POINTER(self.XEvent)]
        x.XIconifyWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int]
        x.XFree.argtypes = [ctypes.c_void_p]
        x.XFlush.argtypes = [ctypes.c_void_p]
        self.dpy = x.XOpenDisplay(None)
        if not self.dpy:
            raise OSError("cannot open the X display")
        self.root = x.XDefaultRootWindow(self.dpy)
        self.atom = lambda name: x.XInternAtom(self.dpy, name.encode(), 0)

    def riot_windows(self):
        x = self.x
        typ, fmt, n, after, data = ctypes.c_ulong(), ctypes.c_int(), ctypes.c_ulong(), ctypes.c_ulong(), ctypes.c_void_p()
        if x.XGetWindowProperty(self.dpy, self.root, self.atom("_NET_CLIENT_LIST"), 0, 4096, 0, 33,  # XA_WINDOW
                                ctypes.byref(typ), ctypes.byref(fmt), ctypes.byref(n), ctypes.byref(after),
                                ctypes.byref(data)) != 0 or not data:
            return []
        wins = list(ctypes.cast(data, ctypes.POINTER(ctypes.c_ulong))[:n.value])
        x.XFree(data)
        found = []
        for w in wins:
            hint = self.ClassHint()
            if x.XGetClassHint(self.dpy, w, ctypes.byref(hint)):
                names = [ctypes.string_at(v).decode(errors="replace") if v else "" for v in (hint.res_name, hint.res_class)]
                for v in (hint.res_name, hint.res_class):
                    if v:
                        x.XFree(v)
                if any(v.lower().startswith("riot client") or v == "RiotClientServices" for v in names):
                    found.append(w)
        return found

    def send(self, w, message, *data):
        ev = self.XEvent()
        ev.xclient.type = 33   # ClientMessage
        ev.xclient.send_event = 1
        ev.xclient.window = w
        ev.xclient.message_type = self.atom(message)
        ev.xclient.format = 32
        for i, v in enumerate(data):
            ev.xclient.data[i] = v
        self.x.XSendEvent(self.dpy, self.root, 0, (1 << 20) | (1 << 19), ctypes.byref(ev))  # SubstructureRedirect|Notify

    def set_hidden(self, hidden):
        wins = self.riot_windows()
        for w in wins:
            # _NET_WM_STATE: 1 = add, 0 = remove
            self.send(w, "_NET_WM_STATE", 1 if hidden else 0,
                      self.atom("_NET_WM_STATE_SKIP_TASKBAR"), self.atom("_NET_WM_STATE_SKIP_PAGER"), 1)
            if hidden:
                self.x.XIconifyWindow(self.dpy, w, 0)
        self.x.XFlush(self.dpy)
        return len(wins)


def hide_while_league_runs():
    """Keep the Riot Client off the taskbar while League runs, then give it back."""
    if os.environ.get("RCLOL_HIDE_RIOT_CLIENT", "1") == "0":
        return
    try:
        bar = Taskbar()
    except OSError as e:
        log(f"cannot hide the Riot Client: {e}")
        return
    hidden = False
    while league_running():
        if not hidden and bar.set_hidden(True):
            log("Riot Client hidden from the taskbar while League runs")
            hidden = True
        time.sleep(POLL)
    if hidden and bar.set_hidden(False):
        log("League closed: Riot Client back on the taskbar")


def guests_running():
    for pid in os.listdir("/proc"):
        try:
            if pid.isdigit() and os.readlink(f"/proc/{pid}/exe").replace(" (deleted)", "") == MLDR:
                return True
        except OSError:
            continue
    return False


def main():
    if os.environ.get("RCLOL_AUTOPLAY", "1") != "0":
        launch()
    # every time League runs (the first time or opened again from the Riot Client), hide the client
    idle = 0
    while idle < 60:
        if league_running():
            hide_while_league_runs()
        idle = 0 if guests_running() else idle + POLL
        time.sleep(POLL)


def launch():
    started = time.monotonic()
    waiting_for = None
    while time.monotonic() - started < GIVE_UP:
        time.sleep(POLL)
        if league_running():
            return
        lock = lockfile()
        if not lock:
            continue
        port, password = lock
        if waiting_for is None:
            log("Riot Client is up (local API)")
            waiting_for = "api"
        try:
            status, _ = request(port, password, "GET", "/rso-auth/v1/authorization")
            if status != 200:
                if waiting_for != "login":
                    log("waiting for the Riot Client sign-in")
                    waiting_for = "login"
                continue
            status, body = request(port, password, "POST",
                                   f"/product-launcher/v1/products/league_of_legends/patchlines/{PATCHLINE}")
        except (OSError, http.client.HTTPException):
            continue            # the client is still starting (or restarting after an update)
        if status in (200, 201, 204) or "already_launched" in body:
            log(f"asked the Riot Client to launch League ({status})")
            # wait for it to show up; if it doesn't (the client was patching it), ask again
            for _ in range(60):
                time.sleep(2)
                if league_running():
                    log("League is running")
                    return
            continue
        if waiting_for != body:
            log(f"launch refused ({status}): {body[:200]}")
            waiting_for = body
    log("gave up: League did not start")


if __name__ == "__main__":
    main()
