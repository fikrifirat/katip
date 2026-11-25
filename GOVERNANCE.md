# Governance

Katip has one maintainer, Fikri Fırat, who decides what is merged and released. That is said plainly so nobody
has to guess.

## How decisions are made

- **Everyday changes** are decided in the pull request. A change that passes its tests, adds no unlisted network
  call and keeps the two engines identical is usually merged.
- **Bigger changes** (a new data type, a new outside source, a new app, anything that changes what leaves the
  device) start as an issue or a design note in [`roadmap/`](roadmap/), so people can comment before code is
  written.
- **The order of work** is in [ROADMAP.md](ROADMAP.md).

## Lines that don't move

- Documents are masked on the user's device. Katip doesn't upload a document to mask it.
- No telemetry or analytics in any app. A new network call is listed in [NETWORK.md](NETWORK.md) before it ships.
- Masking stays free in every official app.
- The source stays open under the AGPL-3.0 (see [CLA.md](CLA.md), point 6).

## As the project grows

When regular contributors appear, they can be given review and merge rights for a part of the repository
(the SDKs, a desktop app, a language). Those roles, and how someone gets one, will be added here when the first
one is given. Money the project receives (sponsors, licences) and what it is spent on will be reported once a
year in the repository.
