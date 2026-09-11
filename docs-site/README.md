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

## Updating content

Page content is authored by hand to match the current oceanVal docs
(`docs/source/*.rst` and the package README) — there's no templating engine,
so if the underlying package docs change, update the corresponding `.html`
file(s) directly. Shared header/nav/footer markup is duplicated across pages
(no static-site generator), so a nav or footer change should be applied to
all nine `.html` files.
