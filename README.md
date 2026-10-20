# DarlingLolAppImage

> [!WARNING]
> **Don't use your main account.** There is a real risk of getting banned: we have already
> seen 3-day bans while testing. Play with a secondary account.

League of Legends (the macOS client) on Linux, packaged as a single AppImage. Run it and the
first launch sets everything up and opens the Riot Client.

It is built on top of [darling-lol](https://github.com/lucannez64/darling-lol) by
[lucannez64](https://github.com/lucannez64), who did the hard part of getting the Mac client
running on [Darling](https://github.com/darlinghq/darling). This repo only packages it so you
don't have to build Darling yourself or install anything system-wide. Unofficial, and not
affiliated with Riot Games.

> [!IMPORTANT]
> **Sign in with the QR code.** The normal username/password login doesn't work: Riot asks for a
> captcha that never shows up, so you can't get past it. Choose the QR option in the Riot Client
> and scan it with the Riot Mobile app.

Options: `--installer` (reinstall the Riot Client, region from `RCLOL_REGION`, default EUW),
`--shell` (a shell inside Darling), `--shutdown` (stop Darling).

Darling stops by itself about 90 seconds after the Riot Client and League are closed (the Riot
Client leaves background agents running, so without this it would keep going). Settings:

| Variable | Default | What |
|---|---|---|
| `RCLOL_REGION` | `EUW` | region for the Riot Client installer |
| `RCLOL_AUTO_SHUTDOWN` | `1` | `0` keeps Darling running after closing everything |
| `RCLOL_AUTO_SHUTDOWN_DELAY` | `90` | seconds to wait before stopping Darling |
| `RCLOL_CLOSE_CLIENT_IN_GAME` | `1` | `0` keeps the League client open during matches (in-client chat) |
| `DARLING_LOL_HOME` | `~/.darling-lol` | where everything is stored |
| `DARLING_LOL_NO_DESKTOP` | unset | `1` skips the applications menu entry the AppImage adds for itself |

Everything goes into one folder, `~/.darling-lol`. If something breaks, or you just want to try
it and leave no trace, delete that folder and you're back to a clean state:

| Path | What |
|---|---|
| `~/.darling-lol/runtime/` | Darling and the darling-lol runtime (~1 GB) |
| `~/.darling-lol/project/` | launcher scripts |
| `~/.darling-lol/prefix/` | the "Mac": Riot Client and the game (~40 GB) |

## How it works without root

Darling normally ships a setuid `darling` binary, because it needs to mount an overlay,
`/dev/shm` and `/proc` and create PID/mount namespaces. This build adds a rootless mode
(`patches/darling-rootless.patch`): when `darling` isn't setuid, it creates an unprivileged user
namespace that maps only your own user (the same mechanism Flatpak and bubblewrap use) and does
those mounts in there. `darlingserver` gets the namespace capabilities and drops them before
starting launchd, so everything inside the "Mac" runs as your normal user. The install is also
relocatable, so it can live in your home instead of `/usr/local`. A setuid `darling` ignores
the new variables, so a classic install isn't affected.

## Requirements

| | |
|---|---|
| **CPU** | x86-64-v2 |
| **GPU** | AMD: tested. Intel: experimental. NVIDIA: not supported |
| **Kernel** | Linux 5.15+ |
| **libc** | glibc 2.39+ |
| **Session** | X11 or XWayland |
| **Needs** | `python3` |

## Troubleshooting

| Problem | Fix |
|---|---|
| The login asks for a captcha that never appears | Sign in with the QR code (Riot Mobile app) |
| The League client closes as soon as it opens, or a second launch does nothing | `./DarlingLol-*.AppImage --shutdown`, then open it again |
| Darling is still running after closing everything | Wait ~90 s, or `--shutdown`. The watcher's log is `~/.darling-lol/watch.log` |
| Anything else | Delete `~/.darling-lol/runtime` (it's unpacked again on the next launch; the game is kept) |

## Reusing an existing darling-lol install

If you already have darling-lol with the game installed, you don't need to download it again.
Hard-link it into the AppImage's prefix (same disk, takes no extra space):

```sh
cp -al ~/.darling/Applications/"League of Legends.app" ~/.darling-lol/prefix/Applications/
cp -a ~/.darling/Users/Shared/"Riot Games"/Metadata/league_of_legends.live* ~/.darling-lol/prefix/Users/Shared/"Riot Games"/Metadata/
```

## Building

```sh
scripts/build.sh                 # full build in a rootless podman container (Ubuntu 24.04 + LLVM 23)
STEP=appimage scripts/build.sh   # only re-assemble the AppImage
```

What the build adds on top of darling-lol:

| File | Purpose |
|---|---|
| `patches/darling-rootless.patch` | `darling`/`darlingserver`: rootless user namespace mode, relocatable install |
| `patches/darling-lol-tools-appimage.patch` | runtime built for generic x86-64-v2; xshm host library path from `$DARLING_XSHM_HOST_LIBRARY` |
| `scripts/build-appdir.sh` | assembles the AppDir and bundles the libraries whose names change between distros (libjpeg 8, libgif 7, libtiff 6, fuse2, libffi 8, LLVM 23) |
| `scripts/build-ffmpeg.sh` | minimal ffmpeg 6.1 (decoders only, no external libraries) with the sonames Darling expects |
| `patches/darling-window-drag.patch` | dragging frameless windows (League/Riot clients) is handed to the window manager (`_NET_WM_MOVERESIZE`), which also works under XWayland |
| `scripts/fix-llvm-path.py` | makes Iridium (Metal shaders) load the bundled LLVM instead of the build machine's path |
| `appdir/AppRun` | launcher and first-run setup |
| `appdir/fonts.conf` | hides Type 1 fonts, which crash the League client |

The AppImage itself (~180 MB) is published as a Release, not committed.

---

Darling and darling-lol keep their licenses (GPL-3.0).
