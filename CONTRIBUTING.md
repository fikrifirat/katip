# Contributing to Katip

Thank you for helping. Katip masks personal data on the user's own device, so every change is judged on
one question first: could it let a value leak, or send something off the device that the user didn't ask
for? Everything else comes after.

Türkçe kısa not: Katkılarınızı memnuniyetle karşılıyoruz. Gerçek kişisel veri içeren hiçbir belge, ekran
görüntüsü veya örnek paylaşmayın; testler yalnızca sentetik verilerle yapılır.

## Ground rules

- **No real personal data, ever.** Not in issues, pull requests, tests, fixtures or screenshots. Use the
  synthetic documents in `ml/berturk/data/` and `docs/samples/`, or invent values. A real T.C. kimlik number
  that passes the checksum is still real data, so make up one that fails it unless the test needs a valid one.
- **No new network calls without saying so.** Every request the apps can make is listed in
  [NETWORK.md](NETWORK.md). A pull request that adds one updates that page and explains why.
- **The two engines stay identical.** The browser (JavaScript) and Python engines give the same spans. If you
  change detection, run the parity tests below.
- **Measure, don't claim.** Accuracy and speed claims come with the command that produced them. Test sets
  stay sealed: choose on dev, report on test (see [lab/README.md](lab/README.md)).

## Set up and test

| Part | Folder | Tests |
| --- | --- | --- |
| Kalkan (Claude connector, MCP) | `connector/` | `cd connector && python -m pytest -q` |
| Klasör (desktop app) | `desktop/` | `cd desktop && python -m pytest -q` |
| Python SDK | `sdk/python/` | `pip install -e "sdk/python[test]" && pytest -q sdk/python/tests` |
| SDK specs (profiles, models) | `sdk/spec/` | `python sdk/tools/check.py --check` |
| Web app | `src/`, built into `docs/` | see *Develop* in the [README](README.md#develop) |
| Browser = Python | `src/tests/` | `src/tests/parity.mjs` + `parity_server.py`, `src/tests/tests_parity_tagger.cjs` + `ml/parity_py.py` |

Python 3.12 is what CI uses for Kalkan and Klasör. The exact package versions are in
`.github/workflows/kalkan.yml` and `klasor.yml`.

## Pull requests

- One change per pull request, with a short description of what changed and how you checked it.
- Commit subjects say the area and the change, for example `Kalkan: keep UETS addresses masked in court profile`.
- Add or update a test. For a missed or wrong mask, a synthetic example that failed before and passes now.
- User-facing text comes in Turkish and English where the surrounding text does.
- Sign the contributor licence agreement (below). A bot asks on your first pull request.

## Contributor licence agreement

Katip is AGPL-3.0, and the maintainer also offers it under a commercial licence ([COMMERCIAL.md](COMMERCIAL.md))
and ships the iOS app through the App Store, whose terms don't fit the AGPL. Both are only possible if the
maintainer can license every contribution that way. [CLA.md](CLA.md) asks for exactly that: you keep the
copyright in your work, and you allow it to be licensed under the AGPL and under other terms. If you can't
agree to that, open an issue describing the change and we'll find another way.

## Security

Found a way to make Katip leak a value, skip its leak check or send data it shouldn't? Please don't open a
public issue. See [SECURITY.md](SECURITY.md).

## Conduct

Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md). How decisions are made:
[GOVERNANCE.md](GOVERNANCE.md).
