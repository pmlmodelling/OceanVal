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
root, not under `docs-site/`), which publishes this directory whenever a push
to `main` touches `docs-site/**`. The only build step is a one-line `sed`
substitution that bakes the latest PyPI release number into the header
version badge (see below) before uploading; everything else is published
as-is.

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

## Version badge

Every page shows the latest OceanVal release next to the header logo
(`<span id="oceanval-docs-version" class="brand-version">`). It's kept
correct two ways: the deploy workflow bakes in the current PyPI version at
publish time (replacing the placeholder `v&hellip;`), and `assets/js/main.js`
re-fetches `https://pypi.org/pypi/oceanval/json` on page load and updates it
client-side, so a newer release still shows correctly even between deploys.
Don't hardcode a version number here — both of those need the literal
`v&hellip;` placeholder to find and replace/update.

## Archived versions

`.github/workflows/docs-archive.yml` runs whenever a GitHub Release is
created. It reads the version from `setup.py` (the source of truth - not the
release's tag name, not PyPI, since PyPI's publish can race this workflow),
copies this directory's nine pages plus `assets/` into `archive/vX.Y.Z/`,
rewrites their `example-report/` links to point back at the one shared copy
two levels up, freezes their header version badge so it never live-updates
(the client-side PyPI fetch in `main.js` only targets pages that still have
the `oceanval-docs-version` id, which archived pages don't), and regenerates
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
