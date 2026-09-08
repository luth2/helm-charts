# GitHub Pages and Release Process

## Structure

Two types of content are served together at <https://luth2.github.io/helm-charts/>:

- **Portal:** MkDocs Material with search, navigation, light/dark mode, and a chart catalog.
- **Helm repository:** the existing `index.yaml` and all previously published chart packages.

The documentation sources remain `Dokumentation/*.md`, the repository README, and
the four chart READMEs. Only the home page, styling, and build helpers are located under
`.github/pages/`; there is no second copy of the operations guide.

The catalog is generated from `charts/*/Chart.yaml` and a snapshot of the published
Helm index. It distinguishes the source state from the package version.
Existing packages are not repackaged retroactively with modified READMEs.

## One-Time Activation

After merging into `main`, configure the following in the GitHub repository:

1. **Settings -> Pages -> Build and deployment -> Source: GitHub Actions**.
2. The **github-pages** environment must allow deployments from `main`;
   observe any existing approval rules.
3. Under **Actions -> Documentation and Helm Pages -> Run workflow**, start a run
   on the `main` branch if no successful run exists yet.
4. Check the home page, search, chart catalog, and Helm access.

Do not switch to `main /docs` or documentation-only output:
this would leave the Helm index and packages missing from their existing URL. A custom
domain is not required. If the domain or repository changes later,
deliberately migrate `site_url`, links, and consumer configuration as well.

## Publishing Without Losing Helm Files

The [chart release workflow](../.github/workflows/Release%20Charts.yml) remains the
**only writer to the gh-pages branch**. It publishes validated charts
and updates the index using chart-releaser. The branch remains the archive of
Helm files, not the source of the new HTML pages.

The [Pages workflow](../.github/workflows/pages.yml):

1. Builds when documentation changes on `main` or after a successful
   **Release Charts** run. It can also be started manually.
2. Reads the current source state from `main` and the current `gh-pages` branch.
3. Includes only public documentation sources and chart metadata,
   defaults, and schemas. No private configurations or local working files are included.
4. Runs regression tests and `mkdocs build --strict`.
5. Copies the **entire gh-pages snapshot** into a new publishing directory
   and adds the generated website files. The index and `.tgz` files must
   not be supplied by the website build; their bytes are compared after copying.
6. Uploads the complete result as a Pages artifact and deploys it.

This also preserves legacy packages. The Pages workflow writes nothing
back to `gh-pages` and does not compete with chart-releaser for Git pushes.
Pages deployments run serially. A chart release completed in the meantime
triggers another Pages run with a new snapshot.
A missing index causes the build to fail rather than serving an empty Helm repository.

Pull requests check the same build and merge process, but receive
no Pages write permissions and are not published. For `workflow_run`,
only code from `main` is executed; no external build artifacts
are incorporated as executable code.

## Local Validation

Using Python 3.12 and a dedicated virtual environment, run from the repository root:

```sh
python -m pip install -r .github/pages/requirements.txt
python -m unittest discover -s .github/pages -p 'test_*.py' -v
python .github/pages/build_portal.py stage
python -m mkdocs build --strict
python -m mkdocs serve
```

Without a Helm snapshot, the local catalog shows the source state and marks the
publication state as unavailable. For a complete test, check out the
`gh-pages` branch separately and specify its directory path for `stage` and
`merge` using `--helm-repository`. Do not switch branches in the main working directory
or delete any release files.

Generated files are located exclusively under `.ci-artifacts/pages/`.
Before running `stage` again, remove these **generated** outputs; the helper
deliberately refuses to reuse an existing source directory
so that deleted documents do not remain in the portal unnoticed.

## Post-Deployment Acceptance Checks

```sh
helm repo add eccosp https://luth2.github.io/helm-charts/
helm repo update
helm search repo eccosp --versions
helm show chart eccosp/ecp-endpoint --version 5.0.1
helm pull eccosp/ecp-endpoint --version 5.0.1
```

Also check navigation, search, mobile rendering, and the package URLs from the
index. Older published versions must remain available for download.
A documentation-only deployment does not require a chart version bump.

## Errors and Recovery

- **Deployment denied:** Check that the Pages source is set to GitHub Actions, and check Actions permissions
   and environment rules. The deployment job requires `pages: write` and `id-token: write`.
- **Build or link check failed:** Correct the source; do not deploy with
   warnings ignored. The last Pages version remains active until the next successful run.
- **Chart missing from Pages despite a GitHub release:** First verify the successful chart release
   and its index push, then restart the Pages workflow.
- **Return to the previous delivery method:** Temporarily switch Pages back to
   `Deploy from a branch -> gh-pages / (root)`. The Helm archive remains there
   unchanged; the new portal is not served in this mode.
