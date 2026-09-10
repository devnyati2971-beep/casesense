#!/bin/bash
# CaseSense E2E smoke test — starts API, runs the core flow, reports.
cd /home/kartik/Desktop/casesense/casesense-backend

# Start API server + arq worker in background
venv/bin/uvicorn app.main:app --port 8010 > /tmp/cs_e2e_api.log 2>&1 &
API_PID=$!
venv/bin/arq worker.worker_settings.WorkerSettings > /tmp/cs_e2e_worker.log 2>&1 &
WORKER_PID=$!
sleep 5

cleanup() {
  kill $API_PID $WORKER_PID 2>/dev/null
}
trap cleanup EXIT

PASS=0; FAIL=0
check() {
  if [ "$1" -ge 200 ] && [ "$1" -lt 300 ]; then
    echo "PASS: $2"; PASS=$((PASS+1))
  else
    echo "FAIL: $2 (HTTP $1)"; FAIL=$((FAIL+1))
  fi
}

BASE=http://localhost:8010
# Unique per-run client IP: the §75.1 limiter keys by IP, so a fresh IP each
# run keeps the smoke test repeatable (register 5/h, guest 2/24h, OTP 1/min).
RUN_STAMP=$(date +%s)
E2E_IP="10.77.$((RUN_STAMP % 200 + 10)).$((RUN_STAMP % 250 + 1))"
IP_HDR="X-Forwarded-For: $E2E_IP"

# 0. Health
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" $BASE/health)
check $HEALTH "GET /health"

# 1. Register a unique user
EMAIL="e2e_${RUN_STAMP}@casesense.in"
REG=$(curl -s -w "\n%{http_code}" -X POST $BASE/api/v1/auth/register -H "$IP_HDR" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"Password123!\",\"full_name\":\"E2E Advocate\"}")
CODE=$(echo "$REG" | tail -1)
check $CODE "POST /auth/register"
TOKEN=$(echo "$REG" | head -n -1 | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['tokens']['access_token'])" 2>/dev/null)
AUTH="Authorization: Bearer $TOKEN"

# 2. GET /auth/me
CODE=$(curl -s -o /dev/null -w "%{http_code}" $BASE/api/v1/auth/me -H "$AUTH")
check $CODE "GET /auth/me"

# 3. Create matter
MATTER_RES=$(curl -s -w "\n%{http_code}" -X POST $BASE/api/v1/matters -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"State v. E2E","case_number":"E2E/2026/1"}')
CODE=$(echo "$MATTER_RES" | tail -1)
check $CODE "POST /matters"
MATTER_ID=$(echo "$MATTER_RES" | head -n -1 | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null)

# 4. List matters
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/matters?limit=10" -H "$AUTH")
check $CODE "GET /matters"

# 5. Query research
RES=$(curl -s -w "\n%{http_code}" -X POST $BASE/api/v1/research/query -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"query":"Bail under Article 21 after 3 years custody without trial"}')
CODE=$(echo "$RES" | tail -1)
check $CODE "POST /research/query"
SID=$(echo "$RES" | head -n -1 | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])" 2>/dev/null)

# 6. Poll research (worker is simulated inline: statuses progress in DB)
sleep 8
STATUS=$(curl -s $BASE/api/v1/research/$SID -H "$AUTH" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
if [ "$STATUS" = "COMPLETED" ]; then
  echo "PASS: Research session COMPLETED"; PASS=$((PASS+1))
else
  echo "FAIL: Research session status=$STATUS (expected COMPLETED)"; FAIL=$((FAIL+1))
fi

# 7. Save a citation
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/api/v1/saved-citations -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"case_name":"Union of India v. K.A. Najeeb","citation_text":"(2021) 3 SCC 713","court":"Supreme Court of India"}')
check $CODE "POST /saved-citations"

# 8. List saved citations
CODE=$(curl -s -o /dev/null -w "%{http_code}" $BASE/api/v1/saved-citations -H "$AUTH")
check $CODE "GET /saved-citations"

# 9. Create draft
DRAFT_RES=$(curl -s -w "\n%{http_code}" -X POST $BASE/api/v1/matters/$MATTER_ID/drafts -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"document_type":"BAIL_APPLICATION","title":"Bail App — E2E"}')
CODE=$(echo "$DRAFT_RES" | tail -1)
check $CODE "POST /matters/{id}/drafts"
DRAFT_ID=$(echo "$DRAFT_RES" | head -n -1 | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

# 10. Get questionnaire
CODE=$(curl -s -o /dev/null -w "%{http_code}" $BASE/api/v1/drafts/$DRAFT_ID/questionnaire -H "$AUTH")
check $CODE "GET /drafts/{id}/questionnaire"

# 11. Get matter brief
CODE=$(curl -s -o /dev/null -w "%{http_code}" $BASE/api/v1/matters/$MATTER_ID/brief -H "$AUTH")
check $CODE "GET /matters/{id}/brief"

# 12. Audit logs for the matter (blueprint §11: GET /audit/matter/{id})
CODE=$(curl -s -o /dev/null -w "%{http_code}" $BASE/api/v1/audit/matter/$MATTER_ID -H "$AUTH")
check $CODE "GET /audit/matter/{id}"

# 13. Unauthenticated access must 401/403
CODE=$(curl -s -o /dev/null -w "%{http_code}" $BASE/api/v1/matters)
if [ "$CODE" = "401" ] || [ "$CODE" = "403" ]; then
  echo "PASS: Unauthenticated blocked ($CODE)"; PASS=$((PASS+1))
else
  echo "FAIL: Unauthenticated returned $CODE"; FAIL=$((FAIL+1))
fi

# ── v2.2 guest tier + §75.1 rate limiting ──────────────────────────────────────

# 14. Guest search 1 — allowed
G1=$(curl -s -w "\n%{http_code}" -X POST $BASE/api/v1/research/query -H "Content-Type: application/json" \
  -H "$IP_HDR" \
  -d '{"query":"Guest flow: anticipatory bail under Section 438 CrPC test"}')
CODE=$(echo "$G1" | tail -1)
check $CODE "POST /research/query (guest #1)"

# 15. Guest search 2 — allowed
G2=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/api/v1/research/query -H "Content-Type: application/json" \
  -H "$IP_HDR" \
  -d '{"query":"Guest flow: Section 113A presumption of dowry death test"}')
check $G2 "POST /research/query (guest #2)"

# 16. Guest search 3 — must be 429 (2 per 24h per IP)
G3=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/api/v1/research/query -H "Content-Type: application/json" \
  -H "$IP_HDR" \
  -d '{"query":"Guest flow: third search must be rate limited"}')
if [ "$G3" = "429" ]; then
  echo "PASS: Guest limit enforced (429 after 2 free)"; PASS=$((PASS+1))
else
  echo "FAIL: Guest search #3 returned $G3 (expected 429)"; FAIL=$((FAIL+1))
fi

# 17. Guest can poll their own session status
GSID=$(echo "$G1" | head -n -1 | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])" 2>/dev/null)
CODE=$(curl -s -o /dev/null -w "%{http_code}" $BASE/api/v1/research/$GSID -H "$IP_HDR")
check $CODE "GET /research/{sid} (guest polls own session)"

# 18. OTP exhaustion guard — second forgot-password within a minute is 429
FP1=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/api/v1/auth/forgot-password -H "Content-Type: application/json" \
  -H "$IP_HDR" -d '{"email":"otpguard@example.com"}')
FP2=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/api/v1/auth/forgot-password -H "Content-Type: application/json" \
  -H "$IP_HDR" -d '{"email":"otpguard@example.com"}')
if [ "$FP1" = "204" ] && [ "$FP2" = "429" ]; then
  echo "PASS: OTP guard — 1 forgot-password / minute ($FP1 then $FP2)"; PASS=$((PASS+1))
else
  echo "FAIL: OTP guard got $FP1 then $FP2 (expected 204 then 429)"; FAIL=$((FAIL+1))
fi

# 19. Login brute-force guard — 11th attempt in 5 minutes is 429
LB="429"
for i in $(seq 1 11); do
  LB=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/api/v1/auth/login -H "Content-Type: application/json" \
    -H "$IP_HDR" -d '{"email":"brute@example.com","password":"WrongPass1"}')
done
if [ "$LB" = "429" ]; then
  echo "PASS: Login brute-force guard — 11th attempt blocked"; PASS=$((PASS+1))
else
  echo "FAIL: Login brute-force last code $LB (expected 429)"; FAIL=$((FAIL+1))
fi

# 20. AI translate is limited but available to the registered user
TR=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/api/v1/translate -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"text":"The court held that bail is the rule.","target_language":"hi"}')
check $TR "POST /translate (AI, rate limited per user)"

kill $API_PID 2>/dev/null
echo ""
echo "=============================="
echo "E2E RESULT: $PASS passed, $FAIL failed"
echo "=============================="
exit $FAIL