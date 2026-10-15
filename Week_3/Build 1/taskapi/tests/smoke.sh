#!/usr/bin/env bash
# Usage: bash tests/smoke.sh   (server must be running on port 3000)
BASE=http://localhost:3000
check() { # name expected_status actual_status
  if [ "$2" = "$3" ]; then echo "PASS $1 ($3)"; else echo "FAIL $1 (expected $2, got $3)"; fi
}

code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

check "list tasks"      200 "$(code $BASE/tasks)"
check "unknown id"      404 "$(code $BASE/tasks/99999)"
check "empty title"     400 "$(code -X POST $BASE/tasks -H 'Content-Type: application/json' -d '{"title":""}')"
check "create"          201 "$(code -X POST $BASE/tasks -H 'Content-Type: application/json' -d '{"title":"smoke test"}')"

ID=$(curl -s $BASE/tasks | python3 -c "import sys,json; print(max(t['id'] for t in json.load(sys.stdin)))")
check "update"          200 "$(code -X PUT $BASE/tasks/$ID -H 'Content-Type: application/json' -d '{"title":"smoke test","done":true}')"
check "delete"          204 "$(code -X DELETE $BASE/tasks/$ID)"
check "delete again"    404 "$(code -X DELETE $BASE/tasks/$ID)"