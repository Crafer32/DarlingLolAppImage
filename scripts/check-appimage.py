#!/usr/bin/env python3
"""Sanity checks for a built DarlingLol AppImage, without running it.

  scripts/check-appimage.py release/DarlingLol-1.3-pre-x86_64.AppImage

- every library in host-bundle finds its dependencies (in the bundle or as a base system library
  every distro has);
- libLLVM exports every LLVM C API function libiridium uses (the minimal LLVM must not lose any);
- the launcher pieces are there (VERSION, BUILD, watch.py, fonts, fonts.conf).
Needs binutils (readelf, nm) and strings.
"""
import os
import re
import subprocess
import sys
import tempfile

# provided by every glibc system, or deliberately taken from the host (GPU, X11, audio)
SYSTEM = re.compile(r"^(ld-linux-x86-64|libc|libm|libdl|libpthread|librt|libresolv|libutil|libgcc_s|libstdc\+\+|"
                    r"libGL|libEGL|libGLX|libGLdispatch|libgbm|libdrm|libvulkan|libX11|libX11-xcb|libXext|libXau|"
                    r"libXdmcp|libXfixes|libXrender|libxcb[^.]*|libwayland[^.]*|libasound|libpulse[^.]*|libdbus-1|"
                    r"libsystemd|libudev|libfontconfig|libfreetype|libexpat|libz|libbsd|libmd|libcap|libgpg-error|"
                    r"libgcrypt|liblzma|libzstd|libbz2|libcrypto|libssl|libselinux|libpcre2-8|libglib-2.0|"
                    r"libgobject-2.0|libgio-2.0|libgmodule-2.0|libblkid|libmount|liblz4)\.so")

failures = []


def fail(msg):
    failures.append(msg)
    print(f"FAIL {msg}")


def ok(msg):
    print(f"ok   {msg}")


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout


def main(appimage):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([os.path.abspath(appimage), "--appimage-extract"], cwd=tmp,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        root = os.path.join(tmp, "squashfs-root")
        share = os.path.join(root, "usr/share/darling-lol")
        bundle = os.path.join(root, "usr/libexec/darling/usr/lib/host-bundle")

        # launcher pieces
        for f in ["VERSION", "BUILD", "watch.py", "fonts.conf", "fonts/DejaVuSans.ttf", "guest-runtime.tar.gz", "system_profiler"]:
            (ok if os.path.exists(os.path.join(share, f)) else fail)(f"usr/share/darling-lol/{f}")
        version = open(os.path.join(share, "VERSION")).read().strip()
        print(f"     version {version}, build {open(os.path.join(share, 'BUILD')).read().strip() if os.path.exists(os.path.join(share, 'BUILD')) else '?'}")

        # host-bundle dependencies
        present = set(os.listdir(bundle))
        for lib in sorted(present):
            path = os.path.join(bundle, lib)
            if os.path.islink(path) or not lib.endswith(tuple(f".so{s}" for s in ["", ".0", ".1", ".2", ".4", ".5", ".6", ".7", ".8"])) and ".so." not in lib:
                continue
            needed = re.findall(r"\(NEEDED\).*\[(.+?)\]", run("readelf", "-d", path))
            missing = [n for n in needed if n not in present and not SYSTEM.match(n)]
            (fail if missing else ok)(f"{lib}" + (f": missing {', '.join(missing)}" if missing else ""))

        # LLVM C API used by Iridium
        iridium = os.path.join(root, "usr/libexec/darling/usr/lib/darling/libiridium.dylib")
        want = set(re.findall(r"^(LLVM[A-Za-z0-9]+)$", run("strings", "-a", iridium), re.M))
        have = {s.split("@")[0] for s in re.findall(r" T (\S+)", run("nm", "-D", "--defined-only", os.path.join(bundle, "libLLVM.so.23.1")))}
        lost = sorted(want - have)
        (fail if lost else ok)(f"libLLVM exports the {len(want)} C API functions libiridium uses" + (f" (missing {', '.join(lost)})" if lost else ""))

        # things we removed on purpose must stay removed
        fw = os.path.join(root, "usr/libexec/darling/System/Library/Frameworks")
        for gone in ["Ruby.framework", "Python.framework"]:
            (fail if os.path.exists(os.path.join(fw, gone)) else ok)(f"{gone} not shipped")

    print(f"\n{'FAILED' if failures else 'PASSED'}: {appimage}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
