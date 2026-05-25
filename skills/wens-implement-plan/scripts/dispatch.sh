#!/bin/sh
# dispatch.sh — render a template prompt and dispatch it via `agd`.
#
# Usage:
#   dispatch.sh --template <name> [--var k=v ...] [--skills a,b,c]
#                [--guidance <text>] [--prompt <path>] [--out <path>]
#                [--timeout <sec>]
#
# Behavior:
#   - Loads templates/<name>.md (relative to this script's parent).
#   - Substitutes every literal {{key}} occurrence from --var pairs.
#   - --skills: comma-list. Substitutes {{skills}} (backticked, comma-joined)
#     and keeps the <!-- SKILLS-BLOCK --> wrapper content. If omitted, the
#     entire SKILLS-BLOCK section is removed from the prompt.
#   - --guidance: free-text paragraph. Substitutes {{guidance}} and keeps the
#     <!-- GUIDANCE-BLOCK --> wrapper. If omitted, the block is removed.
#   - Writes prompt to --prompt (default docs/tmp/<ts>-<name>.md).
#   - Calls `agd dispatch -f <prompt> --timeout <sec>`, captures stdout+stderr
#     to --out (default docs/tmp/<ts>-<name>.out.md).
#   - Emits prompt=, out=, tier=, timeout=, exit= on stderr.
#   - Exit code mirrors agd; 127 if agd missing, 2 if argv malformed.
#
# Paths under docs/tmp/ are gitignored by convention — ensure your repo has it.

set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
TEMPLATE_DIR="$SCRIPT_DIR/../templates"
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
TMP_DIR="$REPO_ROOT/docs/tmp"

TEMPLATE=""
SKILLS=""
GUIDANCE=""
GUIDANCE_SET=0
PROMPT_PATH=""
OUT_PATH=""
TIMEOUT_OVERRIDE=""

VARS_FILE=$(mktemp -t agddisp.XXXXXX)
RENDERED=$(mktemp -t agddisp.XXXXXX)
TMP_NEXT=$(mktemp -t agddisp.XXXXXX)
cleanup() { rm -f "$VARS_FILE" "$RENDERED" "$TMP_NEXT"; }
trap cleanup EXIT

usage() { sed -n '2,21p' "$0" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --template) TEMPLATE="${2:-}"; shift 2 ;;
    --var)
      [ $# -ge 2 ] || usage
      case "$2" in
        *=*)
          case "$2" in *"
"*) echo "dispatch.sh: --var values must not contain newlines" >&2; exit 2 ;; esac
          printf '%s\n' "$2" >> "$VARS_FILE" ;;
        *) echo "dispatch.sh: --var expects key=value, got '$2'" >&2; exit 2 ;;
      esac
      shift 2 ;;
    --skills)   SKILLS="${2:-}"; shift 2 ;;
    --guidance) GUIDANCE="${2:-}"; GUIDANCE_SET=1; shift 2 ;;
    --prompt)   PROMPT_PATH="${2:-}"; shift 2 ;;
    --out)      OUT_PATH="${2:-}"; shift 2 ;;
    --timeout)  TIMEOUT_OVERRIDE="${2:-}"; shift 2 ;;
    -h|--help)  usage ;;
    *) echo "dispatch.sh: unknown arg '$1'" >&2; usage ;;
  esac
done

[ -n "$TEMPLATE" ] || { echo "dispatch.sh: --template is required" >&2; usage; }

TPL_FILE="$TEMPLATE_DIR/${TEMPLATE}.md"
[ -f "$TPL_FILE" ] || { echo "dispatch.sh: template not found: $TPL_FILE" >&2; exit 2; }

# Literal {{key}} → value substitution; awk index/substr (no regex escaping).
render_one() {
  awk -v key="$1" -v val="$2" '
    BEGIN { ph = "{{" key "}}" ; plen = length(ph) }
    {
      s = $0 ; out = ""
      while ((i = index(s, ph)) > 0) {
        out = out substr(s, 1, i-1) val
        s = substr(s, i + plen)
      }
      print out s
    }' < "$RENDERED" > "$TMP_NEXT"
  mv "$TMP_NEXT" "$RENDERED"
  TMP_NEXT=$(mktemp -t agddisp.XXXXXX)
}

# Either strip the marker lines (keep content), or delete the whole block.
toggle_block() {
  # $1=block name (e.g. SKILLS-BLOCK); $2=keep|drop
  awk -v name="$1" -v mode="$2" '
    BEGIN { open = "<!-- " name " -->" ; close_ = "<!-- /" name " -->" ; in_block = 0 }
    {
      if (index($0, open))  { in_block = 1; if (mode == "keep") next; else next }
      if (index($0, close_)) { in_block = 0; if (mode == "keep") next; else next }
      if (mode == "drop" && in_block) next
      print
    }' < "$RENDERED" > "$TMP_NEXT"
  mv "$TMP_NEXT" "$RENDERED"
  TMP_NEXT=$(mktemp -t agddisp.XXXXXX)
}

cp "$TPL_FILE" "$RENDERED"

# GUIDANCE block.
if [ "$GUIDANCE_SET" = 1 ] && [ -n "$GUIDANCE" ]; then
  render_one guidance "$GUIDANCE"
  toggle_block GUIDANCE-BLOCK keep
else
  toggle_block GUIDANCE-BLOCK drop
fi

# SKILLS block.
if [ -n "$SKILLS" ]; then
  SKILLS_VALUE=$(printf '%s' "$SKILLS" | awk -F, '
    { out=""
      for (i=1; i<=NF; i++) {
        gsub(/^[ \t]+|[ \t]+$/, "", $i)
        if ($i == "") continue
        if (out != "") out = out ", "
        out = out "`" $i "`"
      }
      print out
    }')
  render_one skills "$SKILLS_VALUE"
  toggle_block SKILLS-BLOCK keep
else
  toggle_block SKILLS-BLOCK drop
fi

# Apply --var pairs.
while IFS= read -r pair; do
  [ -z "$pair" ] && continue
  k=${pair%%=*}
  v=${pair#*=}
  render_one "$k" "$v"
done < "$VARS_FILE"

UNRESOLVED=$(grep -oE '\{\{[A-Za-z0-9_]+\}\}' "$RENDERED" | sort -u | tr '\n' ' ')
[ -n "$UNRESOLVED" ] && echo "dispatch.sh: warning: unresolved placeholders: $UNRESOLVED" >&2

mkdir -p "$TMP_DIR"
TS=$(date -u +%Y%m%dT%H%M%SZ)
SLUG=$(printf '%s' "$TEMPLATE" | sed 's/[^A-Za-z0-9._-]/-/g')
: "${PROMPT_PATH:=$TMP_DIR/${TS}-${SLUG}.md}"
: "${OUT_PATH:=$TMP_DIR/${TS}-${SLUG}.out.md}"
mkdir -p "$(dirname "$PROMPT_PATH")" "$(dirname "$OUT_PATH")"
cp "$RENDERED" "$PROMPT_PATH"

case "$TEMPLATE" in
  spec-review*)               TIER=spec-review; DEFAULT=900  ;;
  code-implement*)            TIER=implement;   DEFAULT=1800 ;;
  review-implement*)          TIER=implement;   DEFAULT=1800 ;;
  code-review*)               TIER=review;      DEFAULT=900  ;;
  *)                          TIER=review;      DEFAULT=900  ;;
esac
TIMEOUT="${TIMEOUT_OVERRIDE:-$DEFAULT}"

echo "prompt=$PROMPT_PATH" >&2
echo "out=$OUT_PATH" >&2
echo "tier=$TIER timeout=$TIMEOUT" >&2

if ! command -v agd >/dev/null 2>&1; then
  echo "dispatch.sh: 'agd' not on PATH (https://github.com/superyngo/agd)" >&2
  exit 127
fi

agd dispatch -f "$PROMPT_PATH" --timeout "$TIMEOUT" > "$OUT_PATH" 2>>"$OUT_PATH"
RC=$?
echo "exit=$RC" >&2
exit $RC
