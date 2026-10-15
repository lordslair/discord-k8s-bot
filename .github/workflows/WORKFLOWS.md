# GitHub Actions workflows

How the CI/CD in this folder is built, and the rules to follow when changing it.

This document is shared between repositories: it describes the conventions, not one project. Paths are relative to the repository root, and "default branch" means the branch set in the pipelines' `on:` (`main` or `master`).

## Overview

| File | Name | Trigger | Role |
|------|------|---------|------|
| [pipeline-tests.yml](pipeline-tests.yml) | Pipeline Tests | push / PR to the default branch, `workflow_dispatch` | lint + tests + image build, pushes the `edge` image (default branch pushes only) |
| [pipeline-release.yml](pipeline-release.yml) | Pipeline Release | push of a `v*` tag | lint + tests, then builds and pushes the release images |
| [lint.yml](lint.yml) | Lint | `workflow_call` only | reusable flake8 job |
| [tests.yml](tests.yml) | Tests | `workflow_call` only | reusable pytest job |

Only the two `pipeline-*` workflows have real triggers. `lint.yml` and `tests.yml` are reusable workflows: they are never run on their own, only called by the pipelines.

```
pipeline-tests / pipeline-release
├── lint        (uses ./.github/workflows/lint.yml)
├── tests       (uses ./.github/workflows/tests.yml)
└── build-push  (needs: lint, tests)
```

`lint` and `tests` run in parallel; `build-push` only starts when both pass.

## Reusable jobs

### Lint ([lint.yml](lint.yml))

1. Reads the Python version from the `Dockerfile` (`FROM python:X.Y-...`, first match).
2. Sets up that Python, with pip cache keyed on `requirements-lint.txt`.
3. Installs `requirements-lint.txt` (flake8, pinned).
4. Runs `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`.

Only syntax errors and undefined names fail the build. Style settings in `.flake8` (e.g. `max-line-length`) apply to local runs, they are not enforced by CI.

### Tests ([tests.yml](tests.yml))

1. Same Python version detection from the `Dockerfile`.
2. Sets up Python, with pip cache keyed on `requirements.txt` + `requirements-tests.txt`.
3. Installs `requirements.txt` and `requirements-tests.txt`.
4. Runs `pytest` (config in `pytest.ini`, typically `pythonpath = code`, `testpaths = tests`).

pytest exits with code 5 when it collects no test. The job accepts that case with a warning, so a repository can use these workflows before it has tests; every other failure fails the job.

External services (Discord, Kubernetes, ...) are faked in the tests: no token, network access or secret is needed. Keep it that way, since this job also runs on pull requests (where secrets are unavailable).

## Pipelines

Both pipelines share the same `build-push` structure: checkout → Docker Hub login → `docker/metadata-action` (tags) → Buildx → `docker/build-push-action`.

The image is `${{ vars.DOCKER_USERNAME }}/${{ github.event.repository.name }}`: the Docker Hub account plus the GitHub repository name, so the same block works in any repository without changes. Renaming the repository changes the image name.

### Pipeline Tests ([pipeline-tests.yml](pipeline-tests.yml))

| Event | Lint + tests | Build | Push | Tags |
|-------|:-:|:-:|:-:|------|
| push to the default branch | ✅ | ✅ | ✅ | `edge`, short SHA |
| pull request to the default branch | ✅ | ✅ | ❌ | – |
| `workflow_dispatch` (any branch) | ✅ | ✅ | ❌ | – (dry run) |

- The Docker Hub login and the push are both gated on `github.event_name == 'push'`. Pull requests (including Dependabot and forks) get no Docker Hub secret, and must never overwrite `edge` with unmerged code.
- Writes the GitHub Actions build cache (`cache-to: type=gha,mode=max`), so the default branch keeps it warm.
- Concurrency group: `<workflow>-<event_name>-<ref>`.
  - PRs and dry runs: `cancel-in-progress: true` (a new run cancels the previous one).
  - Default branch pushes: queued, never cancelled, so an older run can never push `edge` after a newer one.
  - The event name is part of the group so a dry run on the default branch never takes the place of a queued push.

### Pipeline Release ([pipeline-release.yml](pipeline-release.yml))

Triggered by pushing a `v*` tag (e.g. `v1.2.3`). Always pushes, with these tags:

- `{{version}}` (e.g. `1.2.3`)
- `{{major}}.{{minor}}` (e.g. `1.2`)
- short SHA
- `latest`

- Build cache is **read-only** (`cache-from: type=gha`, no `cache-to`): a tag's cache could only be reused by that same tag, so it reuses the one the default branch's `edge` builds already filled.
- Concurrency group: the workflow name, with `cancel-in-progress: false`. Releases run one at a time, so an older tag can never push `latest` after a newer one.

## Secrets and variables

| Name | Kind | Used by |
|------|------|---------|
| `DOCKER_USERNAME` | repository **variable** (`vars.`) | login + image namespace |
| `DOCKER_PASSWORD` | repository **secret** (`secrets.`) | Docker Hub login |

No other secret or variable is used. Tests and lint need none.

## Conventions

Follow these when adding or editing a workflow:

- **Header comment**: every file starts with a short comment saying what it does and when it runs.
- **Least privilege**: top-level `permissions: contents: read`. Add more only at job level and only when needed.
- **Runner**: `ubuntu-24.04`, pinned (never `ubuntu-latest`).
- **Timeouts**: every job sets `timeout-minutes` (5 for lint/tests, 10 for build-push).
- **Step names**: short label followed by an emoji (`Checkout 🛎️`, `Read Python version 🔍`, `Set up Python X.Y 🐍`, `Install requirements ⏬`, `Lint with flake8 📝`, `Test with PyTest ⚙️`, `Build 🏗️ & Push to Docker Hub 🚀`, ...). Reuse the existing ones for the same kind of step.
- **Actions**: pinned to a major version tag (`actions/checkout@vN`, `docker/build-push-action@vN`, ...). Dependabot bumps them.
- **Python version**: never hard-coded in a workflow. It is read from the `Dockerfile` so CI always runs the same Python as the image. To change Python, change the `Dockerfile` only.
- **Requirements split**: runtime deps in `requirements.txt` (compiled from `requirements.in`), lint-only deps in `requirements-lint.txt`, test-only deps in `requirements-tests.txt`, all pinned. Each job installs only what it needs, and its pip cache is keyed on those same files.
- **No project names**: image names and similar values come from the GitHub context (`github.event.repository.name`, ...) or repository variables, never hard-coded, so the workflows can be copied between repositories as-is.
- **Shared steps go in reusable workflows**: anything both pipelines need (like lint or tests) lives in its own `workflow_call` file and is called with `uses: ./.github/workflows/<file>.yml`, rather than being duplicated.
- **No push without lint + tests**: any job that pushes an image must `needs:` both `lint` and `tests`.
- **Ordering safety**: a workflow that pushes a moving tag (`edge`, `latest`) must use a concurrency group that queues instead of cancelling.
- **Inline comments** explain the *why* of non-obvious settings (concurrency, cache mode, `if:` gates). Keep them up to date when changing those settings.
- **README**: the "GitHub Actions pipelines" section of the repository's `README.md` summarises the pipelines; update it if their triggers or behaviour change.

## Testing workflow changes

From quickest to most realistic. Run at least the first and the last before merging a workflow change.

### 1. Static check: [actionlint](https://github.com/rhysd/actionlint)

Single binary, no Docker. Checks YAML and workflow syntax, `${{ }}` expressions and context names, `needs:`, reusable workflow `uses:`, action inputs, and `run:` scripts (through `shellcheck`, if installed). It runs nothing.

```
actionlint            # from the repository root, checks every file in .github/workflows/
```

### 2. Local run: [act](https://github.com/nektos/act)

Single binary, needs Docker. Runs the workflows in containers that imitate GitHub runners, following the reusable workflows and `if:` gates. Good to check lint and tests and the job graph. Not a guarantee that GitHub behaves the same.

```
act pull_request -l          # list the jobs a PR would run
act pull_request \
  -e pr-event.json \
  -P ubuntu-24.04=catthehacker/ubuntu:act-24.04 \
  --var DOCKER_USERNAME=dummy \
  --concurrent-jobs 1
```

- `-e pr-event.json`: a minimal event payload. `github.event.repository.name` (used for the image name) is empty without it:
  ```json
  { "repository": { "name": "<repo>", "default_branch": "<default branch>" },
    "pull_request": { "number": 1, "base": { "ref": "<default branch>" } } }
  ```
- `-P ubuntu-24.04=...`: maps the pinned runner to an act image (about 2.3 GB, plus the build needs about 1 GB free).
- `--concurrent-jobs 1`: act shares one tool cache between jobs, so `lint` and `tests` installing Python in parallel corrupt each other. On GitHub each job has its own VM.
- Only use `pull_request` or `workflow_dispatch`: on `push` events act really logs in and pushes to Docker Hub.

Known limits with these workflows:

- `docker/metadata-action` fails with `Bad credentials`: it calls the GitHub API with the job token, which act fakes (an empty `-s GITHUB_TOKEN=` does not help). A real read-only token (`-s GITHUB_TOKEN=...`) should get past it.
- The `type=gha` build cache needs GitHub's cache service and does not work under act.
- The `setup-python` pip cache can't be saved (`reserveCache failed`): only a warning.
- Avoid `-j lint` / `-j tests`: it also selects the reusable workflow itself as a standalone job, both runs get the same container name, and one fails with `Conflict. The container name ... is already in use`. Run the whole event instead.

### 3. On GitHub

The only fully realistic run. Push the branch and open a PR to the default branch: Pipeline Tests runs lint, tests and the full image build (with cache), and pushes nothing.

`workflow_dispatch` runs the same dry run on any branch (Actions tab, or `gh workflow run pipeline-tests.yml --ref <branch>`). The workflow file must already exist on the default branch for it to be dispatchable, so it can't test a brand new workflow.

## Dependabot

[.github/dependabot.yml](../dependabot.yml) checks weekly for updates to:

- `pip` (requirements files)
- `github-actions` (action versions in the workflows)
- `docker` (the `Dockerfile` base image, which also changes the Python used by CI)

Dependabot PRs go through **Pipeline Tests** like any other PR.

## Releasing

```
git tag v1.2.3
git push origin v1.2.3
```

Pipeline Release then lints, tests, and pushes `1.2.3`, `1.2`, the short SHA and `latest` to Docker Hub.
