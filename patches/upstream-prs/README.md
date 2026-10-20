# Open darling-lol pull requests

Diffs of pull requests that are still open upstream, kept here to try them in a build before they
are merged (`build.sh` applies `UPSTREAM_PRS`, by default `90 103 111 60-launcher`). They apply on top of the `DARLING_LOL_REF`
that `build.sh` uses. Drop a file once its PR is merged.

| PR | What it fixes |
|---|---|
| [#90](https://github.com/lucannez64/darling-lol/pull/90) | LeagueClientUx's main thread spinning in `select()` (~1.5 cores while idle, slow return after a match) |
| [#103](https://github.com/lucannez64/darling-lol/pull/103) | `SIOCGIFMEDIA` for Vivox, so voice chat finds the network interface |
| [#111](https://github.com/lucannez64/darling-lol/pull/111) | Prefix cleanup no longer kills `launchd`/crashpad processes that belong to another prefix |
| [#60](https://github.com/lucannez64/darling-lol/pull/60) (`pr60-launcher.diff`) | Unset an inherited `MANGOHUD=1` so the Riot installer doesn't abort (launcher part only; the docs/test parts no longer apply) |

`pr105.diff` and `pr107.diff` are merged upstream since `bbfa4c6`; they stay for builds of older refs.
