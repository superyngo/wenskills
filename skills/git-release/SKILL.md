---
name: git-release
description: Use when ready to commit and push changes to remote, or when preparing to release a new version with changelog and tag management
argument-hint: [version]
allowed-tools: Read, Write, Edit, Bash, Grep, AskUserQuestion, mcp__github__create_pull_request, mcp__github__list_tags, mcp__github__get_latest_release
---

# Git Release Workflow

Complete workflow for pushing updates to remote and optionally releasing a new version.

---

## Step 1: Confirm Sync with Remote

Before any operation, ensure local is in sync with remote.

### 1.1 Check current branch

```bash
BRANCH=$(git branch --show-current)
```

If `$BRANCH` is not `main`, warn the user and ask whether to continue on this branch:
- Show the current branch name
- Explain that releasing from a non-main branch may not trigger CI/CD or may target the wrong ref
- Options: **Continue on this branch** / **Switch to main first** / **Cancel**

### 1.2 Fetch latest remote info

```bash
git fetch origin
```

### 1.3 Check sync status

```bash
git status
```

Check for:
- "Your branch is behind" → local is behind
- "Your branch has diverged" → branches diverged
- "Your branch is ahead" → ready to push

### 1.4 If there are differences, show details

**Show commits ahead on remote:**

```bash
git log --oneline HEAD..origin/$BRANCH
```

**Show change stats:**

```bash
git diff HEAD...origin/$BRANCH --stat
```

**If needed, show full diff:**

```bash
git diff HEAD...origin/$BRANCH
```

### 1.5 Let user choose resolution

Ask the user:
- **Rebase (recommended)**: `git pull --rebase origin $BRANCH`
- **Merge**: `git pull origin $BRANCH`
- **Cancel workflow**

If sync produces conflicts, stop and show conflict messages.

---

## Step 2: Code Quality Checks

**Important**: Run before committing to ensure only high-quality code is submitted.

### 2.1 Auto-detect project type

Check in order:

| File | Project Type |
|------|-------------|
| `Cargo.toml` | Rust |
| `package.json` | Node.js |
| `pyproject.toml` or `setup.py` | Python |
| `go.mod` | Go |

### 2.2 Run quality checks

Based on the detected project type, run the appropriate:

1. **Format** — auto-fix code formatting
2. **Lint** — check for code quality issues, auto-fix where possible
3. **Type check** — verify type correctness (if applicable)
4. **Test** — run all tests and ensure they pass

All checks must pass. If any check fails and cannot be auto-fixed, ask the user whether to continue.

Any auto-fixed changes will be included in the Step 3 commit.

### 2.3 Check result handling

- All checks pass: show "✓ Code quality checks passed"
- Auto-fixed changes: these changes will be committed together in Step 3
- Unfixable errors: ask user whether to continue

---

## Step 3: Commit All Changes

### 3.1 Show all changes

```bash
git status
git diff --stat
```

### 3.2 Let user confirm

- Show change summary
- Suggest commit message (based on change content)
- Let user confirm or modify the commit message

### 3.3 Execute commit

```bash
git add -A
git commit -m "<message>"
```

---

## Step 4: Ask User Whether to Release a New Version

### 4.1 Analyze commit history

```bash
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

if [ -n "$LAST_TAG" ]; then
  git log $LAST_TAG..HEAD --pretty=format:"%s"
else
  git log --pretty=format:"%s" --max-count=20
fi
```

### 4.2 Suggest version bump based on Conventional Commits

Analyze commit messages:
- Contains `BREAKING CHANGE` or `!:` → **major** bump (X.0.0)
- Contains `feat:` → **minor** bump (x.Y.0)
- Only `fix:`, `chore:`, `docs:`, `refactor:`, etc. → **patch** bump (x.y.Z)

### 4.3 Show suggestion

```
Last version: v1.2.3
Change summary:
- 3 new features (feat)
- 2 fixes (fix)
- 1 doc update (docs)

Suggested new version: v1.3.0 (minor bump due to new features)
```

### 4.4 Let user choose

Ask the user:

```
Would you like to release a new version?
[1] Yes, use suggested version v1.3.0
[2] Yes, use a custom version
[3] No, just push without release
```

If user chooses [3] (no release):
- Push to remote directly
- Workflow ends

---

## Step 5: Version Release Process

If the user chooses to release a new version, execute in order:

### 5.1 Normalize version format

- Accept input as `v1.2.3` or `1.2.3`
- Internally use `v` prefix format consistently

### 5.2 Update project config version

Based on detected project type:

**Rust (`Cargo.toml`)**:
```toml
version = "x.y.z"  # without v prefix
```

**Node.js (`package.json`)**:
```json
"version": "x.y.z"  // without v prefix
```

**Python (`pyproject.toml`)**:
```toml
version = "x.y.z"  # without v prefix
```

### 5.3 Update CHANGELOG.md

If `CHANGELOG.md` exists, convert the `## [Unreleased]` section to a new version section.
If it does not exist, create a new file with the version section.

```markdown
## [vX.Y.Z] - YYYY-MM-DD

### Added
- List of new features (extracted from feat: commits)

### Changed
- List of changes (extracted from refactor:, chore: commits)

### Fixed
- List of fixes (extracted from fix: commits)

### Docs
- Documentation updates (extracted from docs: commits)
```

Preserve an empty `## [Unreleased]` section for future use.

### 5.4 Update README.md

- Update version badge (if present)
- Update version references (if present)

### 5.5 Commit file changes

```bash
git add -A
git commit -m "chore: release vX.Y.Z"
```

### 5.6 Create Git Tag

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z

<release notes content>"
```

### 5.7 Push to remote

```bash
git push origin $BRANCH
git push origin --tags
```

### 5.8 Check for remote Release Action

After pushing the tag, check if the project has a GitHub Actions workflow that auto-creates releases:

```bash
if [ -f .github/workflows/release.yml ]; then
  echo "✓ Remote release workflow detected, GitHub Actions will auto-create Release"
  SKIP_LOCAL_RELEASE=true
else
  echo "✓ No auto release workflow detected"
  SKIP_LOCAL_RELEASE=false
fi
```

If `SKIP_LOCAL_RELEASE=true`:
- Show message that Release will be auto-created by GitHub Actions
- Provide Actions page link for tracking: `https://github.com/<owner>/<repo>/actions`
- Skip Step 5.9

If `SKIP_LOCAL_RELEASE=false`:
- Continue to Step 5.9

### 5.9 Create GitHub Release (only when no auto workflow)

**This step only executes when the project has no auto release workflow.**

**Tool priority:**

1. **GitHub MCP Server** (preferred)
   - Use MCP tool to create Release

2. **gh CLI** (fallback)
   ```bash
   gh release create vX.Y.Z \
     --title "Release vX.Y.Z" \
     --notes "<release notes>"
   ```

3. **Prompt user to create manually** (last resort)
   ```
   Please create the Release manually on GitHub:
   https://github.com/<owner>/<repo>/releases/new?tag=vX.Y.Z
   ```

Use the collected release notes as the description, mark as latest version.

### 5.10 Show results

**If auto release workflow exists:**
```
✓ Project config version updated
✓ CHANGELOG.md updated
✓ README.md updated (if applicable)
✓ Tag vX.Y.Z created
✓ Pushed to remote

→ GitHub Actions will auto-create Release
→ Track progress: https://github.com/user/repo/actions
→ View after completion: https://github.com/user/repo/releases/tag/vX.Y.Z
```

**If no auto workflow (local creation):**
```
✓ Project config version updated
✓ CHANGELOG.md updated
✓ README.md updated (if applicable)
✓ Tag vX.Y.Z created
✓ Pushed to remote
✓ GitHub Release created

Release link: https://github.com/user/repo/releases/tag/vX.Y.Z
```

---

## Error Handling

- If a git operation fails, show error message and stop the workflow
- If no auto release workflow and GitHub MCP is unavailable, fall back to gh CLI
- If gh CLI is unavailable, fall back to prompting user to create manually
- If file update fails, ask user whether to continue

---

## Usage Examples

```bash
# Quick push (auto checks, commit, ask whether to release)
/git-release

# Release with specific version
/git-release v1.3.0

# Release a patch version
/git-release v1.2.1
```

---

## Notes

### Version Format

Recommended to use Semantic Versioning:
- **Major** (X.0.0): incompatible API changes
- **Minor** (x.Y.0): backward-compatible new features
- **Patch** (x.y.Z): backward-compatible bug fixes

### Conventional Commits Type Mapping

| Type | Description | Version Impact |
|------|-------------|----------------|
| `feat:` | New feature | minor |
| `fix:` | Bug fix | patch |
| `docs:` | Documentation | patch |
| `style:` | Formatting | patch |
| `refactor:` | Refactoring | patch |
| `perf:` | Performance | patch |
| `test:` | Tests | patch |
| `chore:` | Maintenance | patch |
| `BREAKING CHANGE` | Breaking change | major |

### Branch Protection

If the main branch has protection rules, direct push may not be possible.

### Permissions Required

Ensure you have push permissions and Release creation permissions.

### Auto Release Workflow Detection

- After pushing a tag, checks whether `.github/workflows/release.yml` exists
- If it exists, the project has a GitHub Actions workflow for auto-creating Releases
- In this case, the local Release creation step is skipped to avoid duplication
- Common auto release workflow trigger:
  ```yaml
  on:
    push:
      tags:
        - "v*.*.*"
  ```
- If your project uses a different filename (e.g., `ci.yml`, `build.yml`), you may need to manually adjust the detection logic

---
