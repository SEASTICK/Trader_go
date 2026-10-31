#!/usr/bin/env bash
# Pausar en stable-release tills en godkännare svarar i ett ärende (issue).
#
# GitHub tillåter inte "required reviewers" i privata repon på gratisplanen, så godkännandet sker i
# kommentarer. Bara användarna i APPROVERS räknas. "approve" publicerar, "deny" avbryter.
#
# Miljövariabler: GH_TOKEN, GH_REPO, APPROVERS (blankstegsseparerade), RELEASE_VERSION, RUN_URL.
# Valfria: TRIGGERED_BY (den som startade körningen, får ärendet och mejlet), POLL_SECONDS (standard 30).
set -uo pipefail

poll="${POLL_SECONDS:-30}"
# Bara den som startade körningen får mejl. Startades den av någon annan än en godkännare (till exempel via en tagg)
# tilldelas alla godkännare, så att någon alltid ser förfrågan.
triggered="${TRIGGERED_BY:-}"
assignees=()
for user in $APPROVERS; do
  if [ "${user,,}" = "${triggered,,}" ]; then assignees=(--assignee "$user"); break; fi
done
if [ ${#assignees[@]} -eq 0 ]; then for user in $APPROVERS; do assignees+=(--assignee "$user"); done; fi

body="Trader_go **v${RELEASE_VERSION}** är byggd men inte publicerad. När den godkänns går uppdateringen ut till alla som har appen.

Svara i det här ärendet med **approve** för att publicera eller **deny** för att avbryta.
Bara ${APPROVERS// /, } kan godkänna. Ärendet är tilldelat den som startade körningen, men båda kan svara.

Bygget: ${RUN_URL}"

issue_url="$(gh issue create --title "Godkänn uppdatering v${RELEASE_VERSION} till användarna" --body "$body" "${assignees[@]}")" || exit 1
issue="${issue_url##*/}"
echo "Väntar på godkännande i $issue_url"

trap 'gh issue close "$issue" --comment "Körningen avslutades utan beslut." >/dev/null 2>&1 || true' EXIT

# Första svaret från en godkännare avgör. Kommentarer från andra ignoreras.
find_decision() {
  local comments
  comments="$(gh api "repos/${GH_REPO}/issues/${issue}/comments" --paginate \
    --jq '.[] | [.user.login, (.body | gsub("^\\s+|\\s+$"; "") | ascii_downcase)] | @tsv')" || return 0
  local author text user
  while IFS=$'\t' read -r author text; do
    for user in $APPROVERS; do
      if [ "${author,,}" = "${user,,}" ]; then
        case "$text" in
          approve|approved) echo approve; return 0 ;;
          deny|denied) echo deny; return 0 ;;
        esac
      fi
    done
  done <<< "$comments"
}

while true; do
  sleep "$poll"
  decision="$(find_decision)"
  case "$decision" in
    approve)
      gh issue close "$issue" --comment "Godkänd. Publicerar v${RELEASE_VERSION}." >/dev/null || true
      trap - EXIT
      exit 0
      ;;
    deny)
      gh issue close "$issue" --comment "Avslagen. Ingenting publiceras." >/dev/null || true
      trap - EXIT
      echo "Releasen avslogs av en godkännare." >&2
      exit 1
      ;;
  esac
done
