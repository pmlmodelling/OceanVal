# OceanVal website

Source for the OceanVal marketing/documentation site (`docs-site/` in the main
oceanVal repository). Plain static HTML/CSS/JS — no build step, no dependencies.

## Structure

```
index.html          Landing page
installing.html      \
quickstart.html       \
how-to-use.html         Documentation, mirrors docs/source/*.rst in the
recipes.html             oceanVal package, redesigned
obs-data.html            /
qa.html                 /
api.html               /
about.html          /
assets/
  css/style.css      Design system (design tokens, components)
  js/main.js         Nav, copy-to-clipboard, FAQ accordion, recipe filters, scrollspy
  img/               Logo (from oceanval/data/oceanval_wordmark.svg), PML logo, favicon
archive/             Per-release snapshots of this directory's nine pages +
                      assets/, written by .github/workflows/docs-archive.yml.
                      See "Archived versions" below - don't hand-edit it.
example-report/       Sample validate() output, linked from a few pages.
                      Deliberately excluded from archive/ snapshots (it's
                      large and not version-specific).
```

## Previewing locally

```sh
cd docs-site
python3 -m http.server 8000
# then open http://localhost:8000
```

## Deploying to GitHub Pages

Deployment is automated by `.github/workflows/pages.yml` (at the repository
root, not under `docs-site/`), which publishes this directory as-is (no build
step) whenever a push to `main` touches `docs-site/**`.

To turn it on:

1. In the repo's **Settings → Pages**, set **Source** to **GitHub Actions**
   (not "Deploy from a branch").
2. Push to `main` (or run the workflow manually from the **Actions** tab —
   it has `workflow_dispatch` enabled). The site publishes to
   `https://<org>.github.io/<repo>/`.

If your default branch isn't `main`, update the `branches:` list in the
workflow file to match.

The included `.nojekyll` file stops GitHub Pages from running its default
Jekyll processing, which isn't needed here and can interfere with files/paths
starting with an underscore.

## Version selector

Every page has a `<select id="oceanval-version-select" class="version-select">`
next to the header logo, listing:

- **Development** - `docs-site/`'s root pages, i.e. this directory as it
  currently is on `main`. Labelled "vX.Y.Z (development)", where X.Y.Z is
  the latest PyPI release (this can be ahead of that release - it's whatever
  hasn't been cut into a release yet).
- **Stable** - `archive/versions.json`'s newest entry, i.e. the docs exactly
  as they were at the most recent release. Labelled "vX.Y.Z (stable)".
- Every older archived version below that, plain "vX.Y.Z", no label.

It's entirely client-side, driven by `assets/js/main.js`: on load it fetches
`https://pypi.org/pypi/oceanval/json` for the current version and
`archive/versions.json` for the archived list, populates the `<option>`s,
and wires up a `change` listener that navigates to the same page in the
chosen version - also recording the choice (see "Defaulting to Stable"
below) when Development is picked.

It works identically on a root page, an archived snapshot
(`archive/vX.Y.Z/*.html`), and the archive listing page
(`archive/index.html`) without sniffing the URL: each declares how far "up"
the site root is via `data-root-prefix` on `<body>`, and an archived page
additionally declares its own version via `data-archived-version` (both set
automatically - a root page's is `""`, `docs-archive.yml` sets the other two
when it creates a snapshot). Don't hand-edit either attribute, and don't
delete the placeholder `<option value="">v&hellip;</option>` - the selector
stays disabled showing that text if the fetches fail (offline, blocked), so
it needs to exist.

## Defaulting to Stable

GitHub Pages has no server-side routing, so "the site defaults to Stable"
is implemented as a redirect rather than root actually *being* Stable's
content: every root page's `<head>` has a small inline script, before
anything else, that does a **synchronous** XHR for `archive/versions.json`
and - unless `localStorage.oceanval-prefers-dev === "1"` - immediately
`location.replace()`s to the same page under the newest archived version.
Synchronous is deliberate: it blocks rendering until the redirect decision
is made, so there's no flash of Development before bouncing to Stable; the
request is same-origin and tiny, so the cost is negligible. Picking
Development from the selector sets that localStorage flag (and picking
anything else clears it), so once someone's chosen Development they won't
keep getting redirected back - only new visitors default to Stable.

This script only belongs in the nine root pages' `<head>` - never in
`archive/**`, which must never redirect anywhere.

## Archived versions

`.github/workflows/docs-archive.yml` runs whenever a GitHub Release is
created. It reads the version from `setup.py` (the source of truth - not the
release's tag name, not PyPI, since PyPI's publish can race this workflow),
copies this directory's nine pages plus `assets/` into `archive/vX.Y.Z/`,
rewrites their `example-report/` links to point back at the one shared copy
two levels up, sets `data-root-prefix`/`data-archived-version` on `<body>`
so the version selector (see above) knows where it is, and regenerates
`archive/index.html` and `archive/versions.json` (newest first) from every
version archived so far. It then commits and pushes that to `main` and
explicitly dispatches `pages.yml` (a `GITHUB_TOKEN` push doesn't trigger
other workflows on its own, so this can't just rely on the normal push
trigger).

Existing snapshots are never touched by a later release - only a brand new
`archive/vX.Y.Z/` directory gets created each time. If that directory already
exists (e.g. the workflow re-ran for some reason), it's left alone rather
than overwritten.

## Updating content

Page content is authored by hand to match the current oceanVal docs
(`docs/source/*.rst` and the package README) — there's no templating engine,
so if the underlying package docs change, update the corresponding `.html`
file(s) directly. Shared header/nav/footer markup is duplicated across pages
(no static-site generator), so a nav or footer change should be applied to
all nine `.html` files.
