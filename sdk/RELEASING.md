# Releasing katip-mask

Both packages are released together from one tag, by `.github/workflows/sdk-release.yml`: it runs the
whole SDK test suite (including the parity and model tests), builds the wheel, sdist and npm tarball,
publishes to PyPI and npm with provenance, and makes a GitHub pre-release with the files.

## One-time setup (owner)

**PyPI** (no token needed, ever):
1. Sign in at pypi.org (2FA on).
2. Account → Publishing → *Add a new pending publisher*: PyPI project `katip-mask`, owner `fikrifirat`,
   repository `katip`, workflow `sdk-release.yml`, environment `pypi`.

**npm** (a token for the first publish only, since npm trusted publishing needs the package to exist):
1. Sign in at npmjs.com (2FA on).
2. Create a granular access token (packages: read and write, all packages, bypass 2FA) and save it as the
   repository secret `NPM_TOKEN`. Without it, a release publishes to PyPI only and skips npm with a
   warning; re-run the npm job after adding the secret.
3. After the first publish: npmjs.com → `katip-mask` → Settings → *Trusted publisher* → GitHub Actions,
   owner `fikrifirat`, repository `katip`, workflow `sdk-release.yml`, environment `npm`. Set the
   repository variable `NPM_TRUSTED_PUBLISHING` to `true`, then delete the token and the secret.

**GitHub**: Settings → Environments → create `pypi` and `npm` (optionally with yourself as required
reviewer, so every publish waits for a click).

## Each release

1. Update `version` in `sdk/python/pyproject.toml`, `sdk/python/src/katip_mask/__init__.py`,
   `sdk/js/package.json` and `VERSION` in `sdk/js/src/index.ts`; `python sdk/tools/check.py --check`
   fails if they differ.
2. Move the *unreleased* entry in `sdk/CHANGELOG.md` under the version. A new rule or a changed default
   is at least a minor version.
3. Merge to `main`, then tag that commit: `git tag sdk-v0.1.0 && git push origin sdk-v0.1.0`.
4. Check https://pypi.org/project/katip-mask/ and https://www.npmjs.com/package/katip-mask.

## When the engine changes

The engine is `docs/katip_py.zip` (built by `src/build_core.py`, the same file Kalkan ships as
`engine.zip`). After it changes: `python sdk/tools/check.py` (re-vendors it and regenerates the
JavaScript tables), then run the tests. A parity failure points at the TypeScript that needs porting.
Release the SDKs with the same engine as the Kalkan release they go out with; `CHANGELOG.md` names the
engine hash.

## Adoption numbers

Downloads: https://pypistats.org/packages/katip-mask and
https://npm-stat.com/charts.html?package=katip-mask (or `npm view katip-mask` / the npm package page).
