#!/usr/bin/env bash
# Store API key (and optional base URL) in .env for persistent use across
# terminal sessions and Cursor.  .env is gitignored and loaded automatically
# at server startup.
#
# Updates MCP_SAW_API_KEY in place when .env already exists, preserves
# unrelated entries and comments, and only touches MCP_SAW_BASE_URL when
# --base-url is supplied.
#
# Usage:
#   ./scripts/setup-env.sh                              # production (default)
#   ./scripts/setup-env.sh --base-url https://api.x.y   # custom API endpoint
#   op read ... | ./scripts/setup-env.sh                 # pipe from secret manager
#   ./scripts/setup-env.sh YOUR_KEY                      # argument (exposes key in history)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

PROD_CONSOLE="https://plus.probely.app/api-keys"
ENV_FILE=".env"
BASE_URL=""
API_KEY=""
CREATED=0

# ── Parse arguments ──────────────────────────────────────────────────────────
while [ "$#" -gt 0 ]; do
  case "$1" in
    --base-url|-u)
      shift
      BASE_URL="${1:-}"
      if [ -z "$BASE_URL" ]; then
        echo "Error: --base-url requires a URL argument." >&2
        exit 1
      fi
      shift
      ;;
    -*)
      echo "Error: unknown option '$1'" >&2
      exit 1
      ;;
    *)
      API_KEY="$1"
      echo "Warning: passing keys as arguments exposes them in shell history."
      echo "Prefer: ./scripts/setup-env.sh  (interactive prompt)"
      shift
      ;;
  esac
done

# ── Read API key (interactive or piped) ──────────────────────────────────────
if [ -z "$API_KEY" ]; then
  if [ -t 0 ]; then
    if [ -z "$BASE_URL" ]; then
      printf "Paste your API key (from %s): " "$PROD_CONSOLE"
    else
      printf "Paste your API key for %s: " "$BASE_URL"
    fi
    read -rs API_KEY
    echo
  else
    # Bash `read` returns nonzero when input ends at EOF without a
    # trailing newline, even after capturing a nonempty value. With
    # `set -e` that aborts before the empty-key check. Tolerate EOF
    # here; the check below still rejects an empty key.
    read -r API_KEY || true
  fi
fi

if [ -z "${API_KEY:-}" ]; then
  echo "Error: empty API key." >&2
  exit 1
fi

# The temp file below holds the API key and sits next to .env. Remove it on
# any exit, including `set -e` aborts and INT/TERM/HUP. SIGKILL cannot run this
# trap; `.env.*` is therefore also gitignored and excluded by package.sh.
TMP_ENV_FILE=""
cleanup_tmp_env() {
  if [ -n "$TMP_ENV_FILE" ]; then
    rm -f "$TMP_ENV_FILE"
  fi
}
trap cleanup_tmp_env EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

# ── .env record scanner ──────────────────────────────────────────────────────
# Records are split the way the server's reader (python-dotenv, see
# snyk_apiweb/config.py) splits them, so a quoted value that spans lines is one
# record and text inside it is never mistaken for an assignment. Bash only: the
# script must work before any Python dependency is installed.
#
#   record = whitespace* ["export" blank+] key [blank* "=" blank* value]
#            [blank* "#" comment] blank* EOL
#   key    = 'single quoted' | run of characters other than "=", "#", space
#   value  = 'single' | "double" (a backslash escapes the next character, and
#            the value may span lines) | rest of the line
#
# A line that does not parse is one opaque record that ends at its line end.
LC_ENV_BLANK=$' \t\v\f'
LC_ENV_NL=$'\n'
LC_ENV_CR=$'\r'
RE_ENV_LEAD='^[[:space:]]*'
RE_ENV_EXPORT="^export[$LC_ENV_BLANK]+"
RE_ENV_SQ_KEY="^'[^']+'"
RE_ENV_KEY="^[^=#[:space:]]+"
RE_ENV_BLANKS="^[$LC_ENV_BLANK]*"
RE_ENV_EQ="^=[$LC_ENV_BLANK]*"
RE_ENV_SQ_VALUE="^'(\\\\.|[^'\\\\])*'"
RE_ENV_DQ_VALUE='^"(\\.|[^"\\])*"'
RE_ENV_RAW_VALUE="^[^$LC_ENV_CR$LC_ENV_NL]*"
RE_ENV_COMMENT="^[$LC_ENV_BLANK]*#[^$LC_ENV_CR$LC_ENV_NL]*"
RE_ENV_EOL="^[$LC_ENV_BLANK]*($LC_ENV_CR$LC_ENV_NL|$LC_ENV_NL|$LC_ENV_CR|\$)"
RE_ENV_LINE="^[^$LC_ENV_CR$LC_ENV_NL]*($LC_ENV_CR$LC_ENV_NL|$LC_ENV_NL|$LC_ENV_CR)?"

# Parse the record at the start of $1 (leading whitespace already removed).
# Sets REC_BODY (the record without its line ending), REC_EOL, REC_EXPORT,
# REC_KEYTEXT and REC_KEY. REC_KEY is empty unless the record is a valid
# assignment or bare key.
parse_env_record() {
  local s="$1" consumed="" eq c
  REC_BODY="" REC_EOL="" REC_EXPORT="" REC_KEYTEXT="" REC_KEY=""

  if [[ $s =~ $RE_ENV_EXPORT ]]; then
    REC_EXPORT="${BASH_REMATCH[0]}"
    consumed="$REC_EXPORT"
    s="${s:${#REC_EXPORT}}"
  fi
  if [ "${s:0:1}" = "#" ]; then
    [[ $s =~ $RE_ENV_LINE ]]
    REC_BODY="$consumed${BASH_REMATCH[0]}"
    return 0
  fi
  if [ "${s:0:1}" = "'" ]; then
    [[ $s =~ $RE_ENV_SQ_KEY ]] || { env_opaque_line "$consumed" "$s"; return 0; }
    REC_KEYTEXT="${BASH_REMATCH[0]}"
    REC_KEY="${REC_KEYTEXT:1:${#REC_KEYTEXT}-2}"
  else
    [[ $s =~ $RE_ENV_KEY ]] || { env_opaque_line "$consumed" "$s"; return 0; }
    REC_KEYTEXT="${BASH_REMATCH[0]}"
    REC_KEY="$REC_KEYTEXT"
  fi
  consumed="$consumed$REC_KEYTEXT"
  s="${s:${#REC_KEYTEXT}}"

  [[ $s =~ $RE_ENV_BLANKS ]]
  consumed="$consumed${BASH_REMATCH[0]}"
  s="${s:${#BASH_REMATCH[0]}}"

  if [ "${s:0:1}" = "=" ]; then
    [[ $s =~ $RE_ENV_EQ ]]
    eq="${BASH_REMATCH[0]}"
    consumed="$consumed$eq"
    s="${s:${#eq}}"
    c="${s:0:1}"
    if [ "${#eq}" -gt 1 ] && [ "$c" = "#" ]; then
      :  # `KEY= # note`: empty value, the rest is a comment
    elif [ "$c" = "'" ]; then
      [[ $s =~ $RE_ENV_SQ_VALUE ]] || { env_opaque_line "$consumed" "$s"; return 0; }
      consumed="$consumed${BASH_REMATCH[0]}"
      s="${s:${#BASH_REMATCH[0]}}"
    elif [ "$c" = '"' ]; then
      [[ $s =~ $RE_ENV_DQ_VALUE ]] || { env_opaque_line "$consumed" "$s"; return 0; }
      consumed="$consumed${BASH_REMATCH[0]}"
      s="${s:${#BASH_REMATCH[0]}}"
    elif [ -n "$c" ] && [ "$c" != "$LC_ENV_NL" ] && [ "$c" != "$LC_ENV_CR" ]; then
      [[ $s =~ $RE_ENV_RAW_VALUE ]]
      consumed="$consumed${BASH_REMATCH[0]}"
      s="${s:${#BASH_REMATCH[0]}}"
    fi
  fi

  if [[ $s =~ $RE_ENV_COMMENT ]]; then
    consumed="$consumed${BASH_REMATCH[0]}"
    s="${s:${#BASH_REMATCH[0]}}"
  fi
  [[ $s =~ $RE_ENV_EOL ]] || { env_opaque_line "$consumed" "$s"; return 0; }
  REC_BODY="$consumed"
  REC_EOL="${BASH_REMATCH[0]}"
}

# python-dotenv treats Unicode whitespace (NBSP, EM SPACE, IDEOGRAPHIC SPACE,
# the C1/C0 separators ...) as whitespace too. The scanner's regexes only know
# ASCII classes, so it parses a copy in which every such character is replaced
# by the same number of ASCII spaces. Lengths stay equal, so offsets found in
# the copy slice the original bytes, which are what gets written back.
normalize_env_whitespace() {
  local seq
  NORMALIZED_ENV="$1"
  for seq in $'\x1c' $'\x1d' $'\x1e' $'\x1f'; do
    NORMALIZED_ENV="${NORMALIZED_ENV//"$seq"/ }"
  done
  for seq in $'\xc2\x85' $'\xc2\xa0'; do
    NORMALIZED_ENV="${NORMALIZED_ENV//"$seq"/  }"
  done
  for seq in $'\xe1\x9a\x80' $'\xe2\x80\x80' $'\xe2\x80\x81' $'\xe2\x80\x82' \
    $'\xe2\x80\x83' $'\xe2\x80\x84' $'\xe2\x80\x85' $'\xe2\x80\x86' $'\xe2\x80\x87' \
    $'\xe2\x80\x88' $'\xe2\x80\x89' $'\xe2\x80\x8a' $'\xe2\x80\xa8' $'\xe2\x80\xa9' \
    $'\xe2\x80\xaf' $'\xe2\x81\x9f' $'\xe3\x80\x80'; do
    NORMALIZED_ENV="${NORMALIZED_ENV//"$seq"/   }"
  done
}

# A record that does not parse: keep it verbatim up to the end of its line and
# never treat it as an assignment.
env_opaque_line() {
  [[ $2 =~ $RE_ENV_LINE ]]
  REC_BODY="$1${BASH_REMATCH[0]}"
  REC_EOL="" REC_EXPORT="" REC_KEYTEXT="" REC_KEY=""
}

# Upsert KEY=VALUE in ENV_FILE. The first assignment of KEY (however spelled:
# `export KEY=...`, `KEY = ...`, indented, quoted key, after a BOM) is replaced
# in place and keeps its `export`/indentation, later assignments of KEY are
# dropped, and the line is appended when KEY is missing. Every other record
# (comments, blank lines, other keys, multi-line values) is copied byte for
# byte, including its line ending and a missing final newline.
upsert_env_var() {
  local key="$1"
  local value="$2"
  local LC_ALL=C
  local tmp buf="" bom="" rest nrest lead out found=0
  local export_text keytext body eol
  local utf8_bom=$'\xef\xbb\xbf'

  # Same directory as ENV_FILE so the final mv is an atomic rename.
  tmp="$(mktemp "$(dirname "$ENV_FILE")/.env.XXXXXX")"
  TMP_ENV_FILE="$tmp"

  if [ -f "$ENV_FILE" ]; then
    # The trailing x keeps trailing newlines, which $(...) would strip; a
    # failing cat aborts instead of being mistaken for an empty file.
    buf="$(cat -- "$ENV_FILE" && printf x)" || return 1
    buf="${buf%x}"
  fi
  if [ "${buf:0:3}" = "$utf8_bom" ]; then
    bom="$utf8_bom"
    buf="${buf:3}"
  fi

  rest="$buf"
  normalize_env_whitespace "$rest"
  nrest="$NORMALIZED_ENV"
  out="$bom"
  while [ -n "$rest" ]; do
    [[ $nrest =~ $RE_ENV_LEAD ]]
    lead="${rest:0:${#BASH_REMATCH[0]}}"
    rest="${rest:${#lead}}"
    nrest="${nrest:${#lead}}"
    if [ -z "$rest" ]; then
      out="$out$lead"
      break
    fi
    parse_env_record "$nrest"
    export_text="${rest:0:${#REC_EXPORT}}"
    keytext="${rest:${#REC_EXPORT}:${#REC_KEYTEXT}}"
    body="${rest:0:${#REC_BODY}}"
    eol="${rest:${#REC_BODY}:${#REC_EOL}}"
    rest="${rest:$((${#REC_BODY} + ${#REC_EOL}))}"
    nrest="${nrest:$((${#REC_BODY} + ${#REC_EOL}))}"
    if [ "$REC_KEY" = "$key" ]; then
      if [ "$found" -eq 0 ]; then
        found=1
        out="$out$lead$export_text$keytext=$value${eol:-$LC_ENV_NL}"
      else
        # Keep blank lines before the dropped record, not its indentation.
        out="$out${lead%"${lead##*[$LC_ENV_NL$LC_ENV_CR]}"}"
      fi
    else
      out="$out$lead$body$eol"
    fi
  done

  if [ "$found" -eq 0 ]; then
    case "$out" in
      "" | *"$LC_ENV_NL" | *"$LC_ENV_CR") ;;
      *) out="$out$LC_ENV_NL" ;;
    esac
    out="$out$key=$value$LC_ENV_NL"
  fi
  printf '%s' "$out" > "$tmp"

  if [ -L "$ENV_FILE" ]; then
    # Write through a symlinked .env instead of replacing the link.
    cat "$tmp" > "$ENV_FILE" || return 1
    rm -f "$tmp"
  else
    mv "$tmp" "$ENV_FILE" || return 1
  fi
  TMP_ENV_FILE=""
}

# ── Write .env ───────────────────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  CREATED=1
  : > "$ENV_FILE"
fi

upsert_env_var "MCP_SAW_API_KEY" "$API_KEY"
if [ -n "$BASE_URL" ]; then
  upsert_env_var "MCP_SAW_BASE_URL" "$BASE_URL"
fi
chmod 600 "$ENV_FILE"

if [ "$CREATED" -eq 1 ]; then
  if [ -z "$BASE_URL" ]; then
    echo "Created .env with your API key (permissions: owner-only)."
  else
    echo "Created .env for $BASE_URL (permissions: owner-only)."
  fi
else
  if [ -z "$BASE_URL" ]; then
    echo "Updated .env with your API key (permissions: owner-only)."
  else
    echo "Updated .env for $BASE_URL (permissions: owner-only)."
  fi
fi
