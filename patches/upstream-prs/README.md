# Open darling-lol pull requests

Diffs of pull requests that are still open upstream, kept here to try them in a build before they
are merged (`UPSTREAM_PRS="90 103" scripts/build.sh`). They apply on top of the `DARLING_LOL_REF`
that `build.sh` uses. Drop a file once its PR is merged.

| PR | What it fixes |
|---|---|
| [#90](https://github.com/lucannez64/darling-lol/pull/90) | LeagueClientUx's main thread spinning in `select()` (~1.5 cores while idle, slow return after a match) |
| [#103](https://github.com/lucannez64/darling-lol/pull/103) | `SIOCGIFMEDIA` for Vivox, so voice chat finds the network interface |
| [#105](https://github.com/lucannez64/darling-lol/pull/105) | Keep trustd running from boot (black Riot Client window) |
| [#107](https://github.com/lucannez64/darling-lol/pull/107) | Raise darlingserver's soft file-descriptor limit when the hard limit is fixed |
