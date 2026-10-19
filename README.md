# DarlingLolAppImage

League of Legends (the macOS client) on Linux in a single file, without root.

This is an AppImage of [darling-lol](https://github.com/lucannez64/darling-lol), the Darling
setup that gets the Mac version of LoL running. The original needs you to build Darling
yourself and install it with `sudo` (the `darling` binary is setuid). I wanted something that
works like Wine: download, run, play. No root, nothing installed outside your home.

## Usage

```sh
chmod +x darling-lol-*.AppImage
./darling-lol-*.AppImage --check   # tells you if your PC can run it
./darling-lol-*.AppImage           # the first time it installs the Riot Client
```

Sign in, install League from the Riot Client and play. The region defaults to EUW; for
another one: `RCLOL_REGION=NA ./darling-lol-*.AppImage`.

Other options: `--installer` (reinstall the Riot Client), `--shell` (a shell inside Darling),
`--shutdown` (stop Darling).

Where it puts things:

- `~/.local/share/darling-lol/` the runtime (about 1 GB, unpacked on first run)
- `~/.darling-lol/` the "Mac": Riot Client and the game (~40 GB). Change it with `DPREFIX=...`

If you already have darling-lol installed you don't need to download the game again; you can
hard-link it (same disk, takes no extra space):

```sh
cp -al ~/.darling/Applications/"League of Legends.app" ~/.darling-lol/Applications/
cp -a ~/.darling/Users/Shared/"Riot Games"/Metadata/league_of_legends.live* ~/.darling-lol/Users/Shared/"Riot Games"/Metadata/
```

## What you need

- A 64-bit x86 PC (any Intel or AMD from the last ~15 years)
- An AMD graphics card with Mesa. That's what I've tested (RX 5700 XT, RX 6600). Intel might
  work; NVIDIA, not for now
- Linux 5.11 or newer, glibc 2.39 or newer (Ubuntu 24.04, Debian 13, Fedora 40, Arch...)
- X11, or Wayland with XWayland
- `python3`

Where I've tried it:

- **Void Linux**: the AppImage works, the League client opens and Metal works
- **Debian 13**: first run and Darling without root, OK
- **Arch, Fedora, openSUSE Tumbleweed**: should work as is
- **Ubuntu 24.04+ / Mint 22+**: they need one extra step, below
- **Alpine, Void musl, ARM**: not supported

### Ubuntu 24.04 and derivatives

Ubuntu blocks user namespaces with AppArmor, and that's what the AppImage uses to avoid root.
Run this and it prints the two commands that allow it (once, with sudo):

```sh
./darling-lol-*.AppImage --apparmor-profile
```

### Hardened kernels

If your kernel has `kernel.unprivileged_userns_clone=0` (`linux-hardened`, for example):

```sh
sudo sysctl -w kernel.unprivileged_userns_clone=1
echo kernel.unprivileged_userns_clone=1 | sudo tee /etc/sysctl.d/90-userns.conf
```

## How root is avoided

Darling needs root for just a few things: mounting an overlay, `/dev/shm` and `/proc`, and
creating its own namespaces. All of that can be done inside an unprivileged user namespace,
the same thing Flatpak and bubblewrap use. The patch in `patches/darling-rootless.patch` does
that when `darling` isn't setuid: it maps only your own user and passes the capabilities to
`darlingserver`, which drops them before starting launchd. Everything in the "Mac" runs as your
normal user.

It also makes the install relocatable (it can live in your home or inside the AppImage instead
of `/usr/local`). A setuid `darling` ignores those variables, so the classic install isn't
affected.

## Building it yourself

```sh
scripts/build.sh                 # everything from scratch, in a podman container
STEP=appimage scripts/build.sh   # only repackage the AppImage
```

The container is Ubuntu 24.04 with LLVM 23, so the result runs on anything with glibc 2.39
or newer. You need about 60 GB free and a while (1-2 hours on a decent PC).

What's in the repo:

- `patches/darling-rootless.patch`: Darling without root
- `patches/darling-lol-tools-appimage.patch`: generic x86-64-v2 build instead of
  `-march=native`, and the xshm library path taken from a variable
- `scripts/build-appdir.sh`: builds the AppImage folder. It bundles the libraries whose name
  changes between distros (ffmpeg 6, libjpeg 8, libgif 7, libtiff 6, fuse2, libffi 8 and LLVM 23)
- `scripts/fix-llvm-path.py`: Iridium (the Metal shader translator) loaded LLVM from a fixed
  path; this makes it use the bundled copy
- `appdir/AppRun`: the launcher
- `appdir/fonts.conf`: hides Type 1 fonts, which crash the League client

The AppImage (~230 MB) goes in the Releases, not in the repo.

---

Not affiliated with Riot Games. Darling and darling-lol keep their licenses (GPL-3.0).
