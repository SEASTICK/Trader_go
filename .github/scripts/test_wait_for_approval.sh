#!/usr/bin/env bash
# Testar wait_for_approval.sh mot en låtsas-gh. Kör: bash .github/scripts/test_wait_for_approval.sh
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
script="$here/wait_for_approval.sh"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin"
cat > "$work/bin/gh" <<'GH'
#!/usr/bin/env bash
# Låtsas-gh. Kommentarerna ligger i $FAKE_COMMENTS som "användare<TAB>text" (rå text, som gh api skulle ge efter --jq).
case "$1 $2" in
  "issue create") echo "$@" >> "$FAKE_LOG"; echo "https://github.com/x/y/issues/42" ;;
  "issue close")  echo "close $*" >> "$FAKE_LOG" ;;
  "api repos/"*)  # emulerar --jq: trimmad, gemener
    while IFS=$'\t' read -r a t; do t="$(echo "$t" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr 'A-Z' 'a-z')"; printf '%s\t%s\n' "$a" "$t"; done < "$FAKE_COMMENTS" ;;
  *) echo "oväntat gh-anrop: $*" >&2; exit 1 ;;
esac
GH
chmod +x "$work/bin/gh"
export PATH="$work/bin:$PATH" GH_REPO=o/r GH_TOKEN=x APPROVERS="SEASTICK edwinfighter42-star" RELEASE_VERSION=1.2.3 RUN_URL=http://run POLL_SECONDS=0
export FAKE_LOG="$work/log" FAKE_COMMENTS="$work/comments"
fail=0
run() { # namn, förväntad exitkod, kommentarer, TRIGGERED_BY, timeout
  : > "$FAKE_LOG"; printf '%b' "$3" > "$FAKE_COMMENTS"
  TRIGGERED_BY="$4" timeout "${5:-5}" bash "$script" >/dev/null 2>&1; code=$?
  if [ "$code" = "$2" ]; then echo "ok   $1 (exit $code)"; else echo "FAIL $1: förväntade $2, fick $code"; fail=1; fi
}
assignees() { grep -o -- '--assignee [^ ]*' "$FAKE_LOG" | awk '{print $2}' | paste -sd, -; }

run "approve av godkännare"            0   'SEASTICK\tApprove\n' SEASTICK
run "approve med blanksteg och versaler" 0 'edwinfighter42-star\t  APPROVE  \n' SEASTICK
run "'approved' räknas"                0   'SEASTICK\tapproved\n' SEASTICK
run "deny ger fel"                     1   'SEASTICK\tdeny\n' SEASTICK
run "deny av andra godkännaren"        1   'edwinfighter42-star\tDeny\n' SEASTICK
run "obehörig approve ignoreras (väntar tills timeout)" 124 'mallory\tapprove\n' SEASTICK 2
run "obehörig deny ignoreras"          124 'mallory\tdeny\n' SEASTICK 2
run "ingen kommentar väntar"           124 '' SEASTICK 2
run "obehörig först, sedan godkännare" 0   'mallory\tdeny\nSEASTICK\tapprove\n' SEASTICK
run "första beslutet gäller (approve före deny)" 0 'SEASTICK\tapprove\nedwinfighter42-star\tdeny\n' SEASTICK
run "första beslutet gäller (deny före approve)" 1 'SEASTICK\tdeny\nedwinfighter42-star\tapprove\n' SEASTICK
run "annan text än approve/deny ignoreras" 124 'SEASTICK\tkanske approve sen\n' SEASTICK 2

check_assignees() { # namn, TRIGGERED_BY, förväntat
  run "tilldelning: $1" 0 'SEASTICK\tapprove\n' "$2"
  got="$(assignees)"
  if [ "$got" = "$3" ]; then echo "ok   tilldelad $got"; else echo "FAIL tilldelning $1: förväntade '$3', fick '$got'"; fail=1; fi
}
check_assignees "SEASTICK startar"          SEASTICK            SEASTICK
check_assignees "skiftläge spelar ingen roll" seastick          SEASTICK
check_assignees "Edwin startar"             edwinfighter42-star edwinfighter42-star
check_assignees "annan startar (alla godkännare)" someone-else  SEASTICK,edwinfighter42-star
check_assignees "tom TRIGGERED_BY"          ""                  SEASTICK,edwinfighter42-star

# Ärendet stängs: vid beslut med kommentar, och vid avbrott utan beslut.
run "stänger vid approve" 0 'SEASTICK\tapprove\n' SEASTICK
grep -q 'Godkänd' "$FAKE_LOG" && echo "ok   stängdes med 'Godkänd'" || { echo "FAIL stängdes inte vid approve"; fail=1; }
run "stänger vid deny" 1 'SEASTICK\tdeny\n' SEASTICK
grep -q 'Avslagen' "$FAKE_LOG" && echo "ok   stängdes med 'Avslagen'" || { echo "FAIL stängdes inte vid deny"; fail=1; }
run "avbrott utan beslut" 124 '' SEASTICK 2
grep -q 'utan beslut' "$FAKE_LOG" && echo "ok   stängdes 'utan beslut' vid avbrott" || { echo "FAIL ärendet lämnades öppet vid avbrott"; fail=1; }

[ "$fail" = 0 ] && echo "ALLA TESTER OK" || { echo "NÅGOT FALLERADE"; exit 1; }
