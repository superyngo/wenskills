---
name: git-release
description: Use when ready to commit and push changes to remote, or when preparing to release a new version with changelog and tag management
argument-hint: [version]
allowed-tools: Read, Write, Edit, Bash, Grep, AskUserQuestion, mcp__github__create_pull_request, mcp__github__list_tags, mcp__github__get_latest_release
---

# Git Release Workflow

Commit + push updates, optionally release a new version.

---

## Step 1: Branch & Sync

### 1.1 Branch check

```bash
BRANCH=$(git branch --show-current)
```

If `$BRANCH` ≠ `main`, warn and ask (releasing off-main may miss CI/CD or target the wrong ref):

- **Continue on this branch** — release stays on `$BRANCH`.
- **Switch to main** — merge `$BRANCH` into `main`, continue the release on `main`. Record `FEAT_BRANCH=$BRANCH` so it can be removed in Step 6.
  ```bash
  FEAT_BRANCH=$BRANCH
  git checkout main && git merge --no-ff "$FEAT_BRANCH"
  BRANCH=main
  ```
  On merge conflict: stop, show conflicts.
- **Cancel**.

### 1.2 Detect uncommitted changes

```bash
git status --porcelain
```

If non-empty, ask the user whether to commit now. If yes, follow Step 3; else stop (a release needs a clean tree).

### 1.3 Sync with remote

```bash
git fetch origin
git status
```

Behind / diverged / ahead → act accordingly. If differences exist, show them:

```bash
git log --oneline HEAD..origin/$BRANCH      # remote-ahead commits
git diff HEAD...origin/$BRANCH --stat       # stats (full diff if needed)
```

Ask how to resolve: **Rebase** (`git pull --rebase origin $BRANCH`, recommended) / **Merge** (`git pull origin $BRANCH`) / **Cancel**. On conflict: stop, show conflicts.

---

## Step 2: Code Quality Checks

Run before committing.

### 2.1 Detect project type

| File | Type |
|------|------|
| `Cargo.toml` | Rust |
| `package.json` | Node.js |
| `pyproject.toml` / `setup.py` | Python |
| `go.mod` | Go |

### 2.2 Run checks

Per type: **format** → **lint** → **type check** (if any) → **test**. All must pass. Auto-fixes are committed in Step 3. If a check fails and can't auto-fix, ask whether to continue.

---

## Step 3: Commit Changes

```bash
git status
git diff --stat
```

Summarize changes, suggest a commit message, let the user confirm/edit, then:

```bash
git add -A
git commit -m "<message>"
```

---

## Step 4: Release or Not

### 4.1 Analyze commits since last tag

```bash
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
[ -n "$LAST_TAG" ] && git log $LAST_TAG..HEAD --pretty=format:"%s" \
                   || git log --pretty=format:"%s" --max-count=20
```

### 4.2 Suggest semver bump (Conventional Commits)

- `BREAKING CHANGE` / `!:` → **major**
- `feat:` → **minor**
- else (`fix:`/`chore:`/`docs:`/`refactor:`…) → **patch**

### 4.3 Ask

Show last version + change summary + suggested version, then:

```
[1] Yes, suggested version  [2] Yes, custom version  [3] No, push only
```

`[3]`: push to remote, then go to Step 6.

---

## Step 5: Release

### 5.1 Normalize version

Accept `v1.2.3` or `1.2.3`; use `v` prefix internally.

### 5.2 Bump config version (no `v` prefix)

- Rust `Cargo.toml`: `version = "x.y.z"`
- Node `package.json`: `"version": "x.y.z"`
- Python `pyproject.toml`: `version = "x.y.z"`

### 5.3 Update CHANGELOG.md

Convert `## [Unreleased]` into a dated version section (create file if absent); leave an empty `## [Unreleased]` behind.

```markdown
## [vX.Y.Z] - YYYY-MM-DD
### Added / Changed / Fixed / Docs
- from feat: / refactor:,chore: / fix: / docs: commits
```

### 5.4 Update README.md

Update version badge / references if present.

### 5.5 Commit + tag

```bash
git add -A
git commit -m "chore: release vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z

<release notes>"
```

### 5.6 Push

```bash
git push origin $BRANCH
git push origin --tags
```

### 5.7 Auto-release detection

```bash
[ -f .github/workflows/release.yml ] && echo "auto" || echo "manual"
```

- **auto**: GitHub Actions creates the Release. Give Actions link `https://github.com/<owner>/<repo>/actions`. Skip 5.8.
- **manual**: continue to 5.8.

### 5.8 Create GitHub Release (manual only)

Priority: **GitHub MCP** → **gh CLI** → **manual link**.

```bash
gh release create vX.Y.Z --title "Release vX.Y.Z" --notes "<notes>"
```

Manual fallback: `https://github.com/<owner>/<repo>/releases/new?tag=vX.Y.Z`

### 5.9 Report

Show updated files, tag, push status, and Release link / Actions link.

---

## Step 6: Cleanup Feature Branch

If `FEAT_BRANCH` was set in Step 1.1 (i.e. user chose Switch to main) and the release/push succeeded, ask to remove the now-merged local branch:

```bash
git branch -d "$FEAT_BRANCH"   # -d = safe; refuses if unmerged
```

Use `-d` only (never `-D`). If git refuses (unmerged), report and leave the branch.

---

## Error Handling

- Git op fails → show error, stop.
- No auto workflow + no MCP → gh CLI → manual link.
- File update fails → ask whether to continue.

---

## Notes

**Semver**: major = breaking; minor = backward-compatible feature; patch = backward-compatible fix.

**Commit type → bump**: `feat`→minor, `BREAKING CHANGE`→major, all others→patch.

**Branch protection**: direct push to protected `main` may fail.

**Auto-release**: triggered by tag push, e.g.

```yaml
on: { push: { tags: ["v*.*.*"] } }
```

If your project uses another filename (`ci.yml`, `build.yml`), adjust 5.7 detection.

## Usage

```bash
/git-release            # commit + ask whether to release
/git-release v1.3.0     # release specific version
```
