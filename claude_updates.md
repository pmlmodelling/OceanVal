# Prompt: keep the docs and website in sync

Paste this whole file to Claude Code after making changes to the `oceanval`
package (new features, API changes, behaviour changes, bug fixes worth
documenting) to make sure the change actually reaches users, not just the
code.

---

## Prompt

I've just made changes to the oceanval package (see recent git history /
the current diff for what changed). Please check whether these places need
updating to match, and update whichever do:

1. **`docs-site/`** — the marketing/documentation site deployed to
   `https://pmlmodelling.github.io/OceanVal/` via
   `.github/workflows/pages.yml`. Plain static HTML, no build step, no
   templating engine — shared header/nav/footer markup is duplicated across
   all ten `.html` files (nine content pages plus `version-history.html`),
   so a structural change (not just page-specific content) needs to be
   applied to all of them. See `docs-site/README.md` for the page-by-page
   structure and how to preview locally.
2. **`docs/source/*.rst`** — the Sphinx/Read the Docs source. `docs-site/`'s
   pages were originally redesigned from these `.rst` files and mirror them
   roughly 1:1 (`api.rst`↔`api.html`, `how_to_use.rst`↔`how-to-use.html`,
   `index.rst`↔`index.html`, `installing.rst`↔`installing.html`,
   `obs_data.rst`↔`obs-data.html`, `q_a.rst`↔`qa.html`,
   `quickstart.rst`↔`quickstart.html`, `recipes.rst`↔`recipes.html`,
   `info.rst`↔`about.html`). Check both, since they can drift independently.
3. **`README.md`** (repo root) — usage examples and the feature list should
   match current behaviour.
4. **`docs-site/example-report/`** — the sample validation report embedded
   in the site. Only worth regenerating if the report's structure/layout
   changed (new sidebar sections, renamed pages, etc.), not for every
   feature change.

Don't hand-edit the "vX.Y.Z" badge next to the logo in each page's header
(`#oceanval-docs-version`) — it needs no manual update, ever.
`docs-site/assets/js/main.js` fetches `https://pypi.org/pypi/oceanval/json`
client-side on page load and fills it in. This badge is a plain "what's
current" indicator, not a version switcher — see `docs-site/README.md`'s
"Version badge" section. (A header dropdown that switched the *whole site*
between versions, plus a synchronous redirect-to-stable-by-default script,
was built and then deliberately reverted — it didn't work reliably. Don't
rebuild that specific design without being asked.)

Don't hand-create or hand-edit anything under `docs-site/archive/`, or the
`<!-- OCEANVAL_VERSION_HISTORY_START -->`/`_END` block inside
`version-history.html` — `.github/workflows/docs-archive.yml` maintains
both automatically on every GitHub Release. It only archives `index.html`
and `api.html` (not the other seven pages — they're not meaningfully
version-specific, and archiving nine pages a release doesn't scale), with
their nav simplified to a single "Version history" link and any link to an
un-archived page rewritten to point at the live copy, under
`archive/vX.Y.Z/`, keyed off the version in `setup.py`. It then updates the
version-history list to match, linking each entry straight to its archived
`api.html`. See `docs-site/README.md`'s "Archived versions" section. The
rest of `version-history.html` (header, nav, footer) is a normal
hand-authored page like the other nine, though its intro copy now
specifically references the API archive, not a general docs archive — keep
that in mind if this scope changes again.

Once you're done, show me a summary of what you changed and why before
committing. Commit only the files that actually needed to change, write a
commit message explaining *why* (not just what), and push to `main` — but
only after I've confirmed I want that, same as any other change.

---

## Pitfalls hit before (don't repeat these)

- **`.gitignore`'s `oceanval_*` rule is anchored to the repo root**
  (`/oceanval_*`). It exists to ignore local build artifacts
  (`oceanval_report/`, `oceanval_results/`, `oceanval_matchups/`,
  `oceanval_report.html`). If you ever see it unanchored again, fix it —
  unanchored, it silently swallows legitimate files anywhere in the tree
  whose name happens to start with `oceanval_`, including
  `docs-site/assets/img/oceanval_wordmark.svg` and
  `docs-site/example-report/oceanval_report.pdf`. That happened once and
  broke the deployed site (missing logo, dead PDF link) without any error.
- **`pages.yml` must stay the *only* Pages-deploying workflow.** A second
  workflow (`static.yml`, copied verbatim from the old standalone
  `oceanval_docs` repo) got added once — it uploaded `path: '.'` (the whole
  package repo, not `docs-site/`) and shared the same `concurrency: group:
  "pages"`. Its runs raced `pages.yml`'s, and whichever ran last "won" and
  published whatever it uploaded — including, once, the entire repo root
  with no `index.html`, which made the live site 404 while GitHub reported
  the deploy as a success. If you're troubleshooting a deploy, check
  `.github/workflows/` for exactly one Pages workflow before assuming
  anything else is wrong.
- **There is no `index.html`** in `docs-site/` or in `validate()`/`compare()`
  report output — both intentionally land straight on a specific page (the
  full-domain summary for `validate()`, the first notebook for `compare()`).
  Don't reintroduce an index/landing page without a reason; it was removed
  on purpose.
- **The repo may show as `pmlmodelling/OceanVal`** (capital V) — it was
  renamed from `pmlmodelling/oceanVal`. Pushes to the old remote URL still
  redirect and succeed, but if you're calling the GitHub API directly,
  either casing works for most endpoints — if one 404s unexpectedly, try
  the other before assuming something's broken.
