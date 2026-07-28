---
name: github-init
description: Use when initializing a new GitHub repository or Gist for the current directory. Handles git init, pre-flight checks, standard skeleton file generation (README, CHANGELOG, LICENSE, .gitignore, PRIVACY.md, release workflow), remote creation, and initial push.
argument-hint: [repo|gist]
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion
---

# GitHub Initialization Workflow

Initialize a GitHub remote repository or Gist for the current directory and generate standard project skeleton files.

---

## Step 0: Determine Mode

Determine execution flow based on argument:
- Argument is `gist` → Skip directly to Step 5 (Gist Workflow).
- Argument is `repo` or omitted → Execute Repository Workflow.
- If ambiguous, ask user: "Create a GitHub Repository or Gist?"

---

## Step 1: Pre-flight & Git Health Checks

Run pre-flight checks for `gh` authentication and Git status:

```bash
# Check GitHub CLI authentication status
gh auth status 2>/dev/null

# Check Git configurations and remotes
git config user.name 2>/dev/null
git config user.email 2>/dev/null
git remote -v 2>/dev/null
git status 2>/dev/null
```

Handling pre-flight results:
- **`gh` CLI not installed/authenticated**: Prompt user to install `gh` (`brew install gh`) or authenticate (`gh auth login`).
- **Git user configuration missing**: Ask user for name/email or set sensible defaults before committing.
- **No Git repository**: Run `git init && git branch -M main`, then proceed.
- **Git repo exists, no remote**: Ensure default branch is set (`git branch -M main`), then proceed to Step 2.
- **Git repo exists with remote**: Inform user that a remote already exists, ask whether to generate missing skeleton files only, then exit.

---

## Step 2: Detect Project Type

Check for marker files in order:

| Marker File | Project Type | Caching Recommendation |
|---|---|---|
| `Cargo.toml` | Rust | `Swatinem/rust-cache@v2` |
| `package.json` | Node.js | `actions/setup-node@v4` with `cache: 'npm'` (or `pnpm`/`yarn`) |
| `go.mod` | Go | `actions/setup-go@v5` with `cache: true` |
| `pyproject.toml` / `setup.py` / `requirements.txt` | Python | `actions/setup-python@v5` with `cache: 'pip'` (or `poetry`/`uv`) |
| None | Generic | Standard GitHub Actions caching as needed |

Also detect if the project produces **binary executables**:
- **Rust**: Presence of `src/main.rs` or `[[bin]]` in `Cargo.toml`.
- **Go**: `main` package.
- **Node.js**: Presence of `bin` field in `package.json`.

---

## Step 3: Generate Skeleton Files

Prompt user to confirm which files to generate (pre-selected based on project type, skipping existing files):

### Standard Required Files (All Repositories)

**README.md** (if missing):

```markdown
# <project-name>

<description>

## Installation

### Windows (PowerShell)
```powershell
$env:APP_NAME="<project-name>"; $env:REPO="superyngo/<project-name>"; irm https://gist.githubusercontent.com/superyngo/a6b786af38b8b4c2ce15a70ae5387bd7/raw/gpinstall.ps1 | iex
```

### Linux / macOS (Bash)
```bash
curl -fsSL https://raw.githubusercontent.com/superyngo/<project-name>/main/install.sh | bash
```

## Usage

...

## License

MIT
```

> **Note**: Include Installation section only if project is a binary project. Description is obtained from user in Step 4.

**CHANGELOG.md** (if missing):

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
```

**LICENSE** (if missing) — MIT, author from `git config user.name` (fallback: `wen`), current year:

```
MIT License

Copyright (c) <YEAR> <AUTHOR>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**.gitignore** (if missing) — Based on project type:

- **Rust**:
  ```
  /target/
  **/*.rs.bk
  ```
- **Node.js**:
  ```
  node_modules/
  dist/
  .env
  ```
- **Python**:
  ```
  __pycache__/
  *.pyc
  .venv/
  dist/
  *.egg-info/
  ```
- **Go**:
  ```
  *.exe
  *.exe~
  *.test
  vendor/
  ```
- **Generic**: Empty or standard OS file ignores (`.DS_Store`, `Thumbs.db`).

**PRIVACY.md** (if missing):

```markdown
# Privacy Policy

This application does not collect, store, or transmit any personal data or sensitive user information.

Last updated: <YEAR>-<MONTH>-<DAY>
```

### Additional Files for Binary Projects

If the project produces binary executables, generate `.github/workflows/release.yml` with comprehensive caching enabled:

```yaml
name: Release Build

on:
  push:
    tags:
      - "v*.*.*"
  workflow_dispatch:
    inputs:
      version:
        description: 'Release version (e.g., v0.3.0)'
        required: true
        type: string

permissions:
  contents: write
  actions: write

env:
  CARGO_TERM_COLOR: always
  CARGO_INCREMENTAL: 0

jobs:
  build:
    name: Build ${{ matrix.target }}
    runs-on: ${{ matrix.os }}
    continue-on-error: false
    strategy:
      fail-fast: false
      matrix:
        include:
          # Linux builds
          - os: ubuntu-latest
            target: x86_64-unknown-linux-gnu
            artifact_name: <project-name>
            asset_name: <project-name>-linux-x86_64
          - os: ubuntu-latest
            target: i686-unknown-linux-gnu
            artifact_name: <project-name>
            asset_name: <project-name>-linux-i686
          - os: ubuntu-latest
            target: x86_64-unknown-linux-musl
            artifact_name: <project-name>
            asset_name: <project-name>-linux-x86_64-musl
          - os: ubuntu-latest
            target: armv7-unknown-linux-gnueabihf
            artifact_name: <project-name>
            asset_name: <project-name>-linux-armv7
          - os: ubuntu-latest
            target: aarch64-unknown-linux-gnu
            artifact_name: <project-name>
            asset_name: <project-name>-linux-aarch64
          - os: ubuntu-latest
            target: aarch64-unknown-linux-musl
            artifact_name: <project-name>
            asset_name: <project-name>-linux-aarch64-musl
            cflags: "-U_FORTIFY_SOURCE"
            cc: "aarch64-linux-gnu-gcc"
          - os: ubuntu-latest
            target: i686-unknown-linux-musl
            artifact_name: <project-name>
            asset_name: <project-name>-linux-i686-musl
          - os: ubuntu-latest
            target: armv7-unknown-linux-musleabihf
            artifact_name: <project-name>
            asset_name: <project-name>-linux-armv7-musl
          # Windows builds
          - os: windows-latest
            target: x86_64-pc-windows-msvc
            artifact_name: <project-name>.exe
            asset_name: <project-name>-windows-x86_64.exe
            rustflags: "-C target-feature=+crt-static"
            opt_level: "3"
            lto: "thin"
            strip: "false"
            codegen_units: "16"
            panic: "unwind"
          - os: windows-latest
            target: i686-pc-windows-msvc
            artifact_name: <project-name>.exe
            asset_name: <project-name>-windows-i686.exe
            rustflags: "-C target-feature=+crt-static"
            opt_level: "3"
            lto: "thin"
            strip: "false"
            codegen_units: "16"
            panic: "unwind"
          - os: windows-latest
            target: aarch64-pc-windows-msvc
            artifact_name: <project-name>.exe
            asset_name: <project-name>-windows-aarch64.exe
            rustflags: "-C target-feature=+crt-static"
            opt_level: "3"
            lto: "thin"
            strip: "false"
            codegen_units: "16"
            panic: "unwind"
          # macOS builds
          - os: macos-15-intel
            target: x86_64-apple-darwin
            artifact_name: <project-name>
            asset_name: <project-name>-macos-x86_64
          - os: macos-latest
            target: aarch64-apple-darwin
            artifact_name: <project-name>
            asset_name: <project-name>-macos-aarch64

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Rust Toolchain
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}

      - name: Cache Rust dependencies and targets
        uses: Swatinem/rust-cache@v2
        with:
          key: ${{ matrix.target }}

      - name: Cache cross binary (musl targets)
        if: matrix.target == 'x86_64-unknown-linux-musl' || matrix.target == 'aarch64-unknown-linux-musl' || matrix.target == 'i686-unknown-linux-musl' || matrix.target == 'armv7-unknown-linux-musleabihf'
        uses: actions/cache@v4
        with:
          path: ~/.cargo/bin/cross
          key: ${{ runner.os }}-cross-v1

      - name: Install cross (for musl targets)
        if: (matrix.target == 'x86_64-unknown-linux-musl' || matrix.target == 'aarch64-unknown-linux-musl' || matrix.target == 'i686-unknown-linux-musl' || matrix.target == 'armv7-unknown-linux-musleabihf')
        run: |
          if ! command -v cross &> /dev/null; then
            cargo install cross --git https://github.com/cross-rs/cross
          fi

      - name: Install 32-bit libraries (Linux i686 only)
        if: matrix.target == 'i686-unknown-linux-gnu'
        run: |
          sudo dpkg --add-architecture i386
          sudo apt-get update
          sudo apt-get install -y gcc-multilib g++-multilib

      - name: Install ARM cross-compilation tools (ARM targets only)
        if: matrix.target == 'armv7-unknown-linux-gnueabihf'
        run: |
          sudo apt-get update
          sudo apt-get install -y gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf

      - name: Install ARM64 cross-compilation tools (ARM64 targets only)
        if: matrix.target == 'aarch64-unknown-linux-gnu'
        run: |
          sudo apt-get update
          sudo apt-get install -y gcc-aarch64-linux-gnu g++-aarch64-linux-gnu

      - name: Configure cargo for ARM cross-compilation
        if: matrix.target == 'armv7-unknown-linux-gnueabihf' || matrix.target == 'aarch64-unknown-linux-gnu'
        run: |
          mkdir -p ~/.cargo
          if [ "${{ matrix.target }}" = "armv7-unknown-linux-gnueabihf" ]; then
            echo '[target.armv7-unknown-linux-gnueabihf]' >> ~/.cargo/config.toml
            echo 'linker = "arm-linux-gnueabihf-gcc"' >> ~/.cargo/config.toml
          elif [ "${{ matrix.target }}" = "aarch64-unknown-linux-gnu" ]; then
            echo '[target.aarch64-unknown-linux-gnu]' >> ~/.cargo/config.toml
            echo 'linker = "aarch64-linux-gnu-gcc"' >> ~/.cargo/config.toml
          fi

      - name: Build (Windows)
        if: matrix.os == 'windows-latest'
        run: cargo build --release --target ${{ matrix.target }}
        env:
          RUSTFLAGS: ${{ matrix.rustflags }}
          CARGO_PROFILE_RELEASE_OPT_LEVEL: ${{ matrix.opt_level }}
          CARGO_PROFILE_RELEASE_LTO: ${{ matrix.lto }}
          CARGO_PROFILE_RELEASE_STRIP: ${{ matrix.strip }}
          CARGO_PROFILE_RELEASE_CODEGEN_UNITS: ${{ matrix.codegen_units }}
          CARGO_PROFILE_RELEASE_PANIC: ${{ matrix.panic }}

      - name: Build with cross (musl targets)
        if: matrix.target == 'x86_64-unknown-linux-musl' || matrix.target == 'aarch64-unknown-linux-musl' || matrix.target == 'i686-unknown-linux-musl' || matrix.target == 'armv7-unknown-linux-musleabihf'
        run: cross build --release --target ${{ matrix.target }}
        env:
          RUSTFLAGS: ${{ matrix.rustflags }}
          CFLAGS: ${{ matrix.cflags }}
          CC: ${{ matrix.cc }}

      - name: Build (Linux and macOS)
        if: matrix.os != 'windows-latest' && matrix.target != 'x86_64-unknown-linux-musl' && matrix.target != 'aarch64-unknown-linux-musl' && matrix.target != 'i686-unknown-linux-musl' && matrix.target != 'armv7-unknown-linux-musleabihf'
        run: cargo build --release --target ${{ matrix.target }}
        env:
          RUSTFLAGS: ${{ matrix.rustflags }}
          CFLAGS: ${{ matrix.cflags }}
          CC: ${{ matrix.cc }}

      - name: Strip binary (Linux and macOS - x86)
        if: matrix.os != 'windows-latest' && matrix.target != 'armv7-unknown-linux-gnueabihf' && matrix.target != 'aarch64-unknown-linux-gnu' && matrix.target != 'aarch64-unknown-linux-musl' && matrix.target != 'i686-unknown-linux-musl' && matrix.target != 'armv7-unknown-linux-musleabihf'
        run: strip target/${{ matrix.target }}/release/${{ matrix.artifact_name }}

      - name: Strip binary (ARM32)
        if: matrix.target == 'armv7-unknown-linux-gnueabihf'
        run: arm-linux-gnueabihf-strip target/${{ matrix.target }}/release/${{ matrix.artifact_name }}

      - name: Strip binary (ARM64)
        if: matrix.target == 'aarch64-unknown-linux-gnu'
        run: aarch64-linux-gnu-strip target/${{ matrix.target }}/release/${{ matrix.artifact_name }}

      - name: Strip binary (cross-compiled musl)
        if: matrix.target == 'x86_64-unknown-linux-musl' || matrix.target == 'aarch64-unknown-linux-musl' || matrix.target == 'i686-unknown-linux-musl' || matrix.target == 'armv7-unknown-linux-musleabihf'
        run: echo "Skipping strip for cross-compiled ${{ matrix.target }} (already stripped by cross)"

      - name: Create tarball (Linux and macOS)
        if: matrix.os != 'windows-latest'
        run: |
          cd target/${{ matrix.target }}/release
          tar czf ${{ matrix.asset_name }}.tar.gz ${{ matrix.artifact_name }}
          mv ${{ matrix.asset_name }}.tar.gz ../../../

      - name: Upload artifacts (Linux and macOS)
        if: matrix.os != 'windows-latest'
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.asset_name }}
          path: ${{ matrix.asset_name }}.tar.gz

      - name: Upload artifacts (Windows)
        if: matrix.os == 'windows-latest'
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.asset_name }}
          path: target/${{ matrix.target }}/release/${{ matrix.artifact_name }}

  release:
    name: Create Release
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          ref: ${{ github.event.inputs.version || github.ref }}

      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts

      - name: Display structure
        run: |
          echo "Current directory structure:"
          ls -la
          echo "Artifacts directory:"
          ls -la artifacts/
          echo "Looking for artifacts:"
          find artifacts -type f \( -name "*.tar.gz" -o -name "*.zip" -o -name "*.exe" \)

      - name: Prepare release files
        run: |
          mkdir -p release_files
          find artifacts -type f -name "*.tar.gz" -exec cp {} release_files/ \;
          for dir in artifacts/*; do
            if [ -d "$dir" ] && [[ "$dir" == *"windows"* ]]; then
              asset_name=$(basename "$dir")
              exe_file="$dir/<project-name>.exe"
              if [ -f "$exe_file" ]; then
                cp "$exe_file" "release_files/$asset_name"
              fi
            fi
          done
          echo "Files in release_files:"
          ls -la release_files/

      - name: Generate checksums
        run: |
          cd release_files
          if [ -n "$(ls -A)" ]; then
            sha256sum * > SHA256SUMS
            echo "Checksums generated:"
            cat SHA256SUMS
          else
            echo "No files found in release_files directory!"
            exit 1
          fi

      - name: Get tag message
        id: tag_message
        run: |
          if [ -n "${{ github.event.inputs.version }}" ]; then
            TAG_NAME="${{ github.event.inputs.version }}"
          else
            TAG_NAME=${GITHUB_REF#refs/tags/}
          fi
          echo "tag_name=$TAG_NAME" >> $GITHUB_OUTPUT
          TAG_MESSAGE=$(git tag -l --format='%(contents)' "$TAG_NAME")
          if [ -z "$TAG_MESSAGE" ]; then
            TAG_MESSAGE="Release $TAG_NAME"
          fi
          echo "message<<EOF" >> $GITHUB_OUTPUT
          echo "$TAG_MESSAGE" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ steps.tag_message.outputs.tag_name }}
          files: release_files/*
          draft: false
          prerelease: false
          body: |
            ${{ steps.tag_message.outputs.message }}

            ---

            ## 📦 Downloads

            Please download the appropriate version for your system from below.

            ## 🔒 File Verification

            Use the SHA256SUMS file to verify the integrity of downloaded files.

            ---

            ## 📝 Auto-generated Changelog
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

> **Important**: Replace all occurrences of `<project-name>` with the actual project name (lowercase) when generating this file.

---

## Step 4: Create GitHub Repo and Push

Before generating skeleton files, collect information from the user:

1. **Repository Description** (used for `gh repo create --description` and `README.md`)
2. **Visibility**: Public (default) or Private?

```bash
PROJECT_NAME=$(basename "$PWD")

gh repo create "$PROJECT_NAME" \
  --public \
  --description "<user-provided description>" \
  --source=. \
  --remote=origin \
  --push
```

- If user chooses Private, replace `--public` with `--private`.
- Display the Repo URL after pushing.

**Execution Order**:

1. Prompt user for description and visibility.
2. Generate skeleton files (fill `README.md` with description).
3. Perform initial commit (`git add -A && git commit -m "chore: initial commit"`).
4. Create GitHub repository and push (`git push -u origin main`).

---

## Step 5: Gist Workflow (When Argument is `gist`)

```bash
# Display files in current directory for selection
ls -la

# Prompt user for:
# 1. Which files to upload (default: all non-hidden files)
# 2. Gist description
# 3. Public or Secret? (default: Public)

gh gist create <files> --desc "<description>" --public
# Or omit --public for secret Gist:
gh gist create <files> --desc "<description>"
```

Display Gist URL after creation.

---

## Step 6: Completion Summary

```
✓ Git repository initialized (default branch: main)
✓ Skeleton files generated: README.md, CHANGELOG.md, LICENSE, .gitignore, PRIVACY.md [, .github/workflows/release.yml]
✓ GitHub repository created: https://github.com/superyngo/<project-name>
✓ Initial commit pushed to main branch

Next Steps:
- Edit README.md to complete project documentation
- Prepare for version release using /git-release
```

---

## Error Handling

- `gh` CLI not installed → Prompt user: `brew install gh` or visit https://cli.github.com
- `gh` not authenticated → Prompt user to run `gh auth login`
- Repository name exists → Inform user and ask to use a different name or set existing repo as remote
- Git operation fails → Display detailed error message and abort workflow

---

## Usage Examples

```bash
# Initialize GitHub repository for current directory (auto-detect project type)
/github-init

# Explicitly specify repository creation
/github-init repo

# Upload current directory files as a Gist
/github-init gist
```
