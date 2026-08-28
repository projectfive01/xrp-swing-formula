#!/usr/bin/env bash
# SOL desk — one command for both paper books + dashboard + lock agent.
# Usage: ./scripts/desk.sh up|down|status|pull|lock|dash
set -euo pipefail
ROOT="${DESK_ROOT:-$HOME/xrp-swing-formula}"
PIDDIR="$ROOT/data/pids"
LOGDIR="$ROOT/data/logs"
VENV="$ROOT/venv/bin/activate"
mkdir -p "$PIDDIR" "$LOGDIR"

alive() {
  local pidfile="$1"
  [[ -f "$pidfile" ]] || return 1
  local pid
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null
}

start_one() {
  local name="$1"
  shift
  local pidfile="$PIDDIR/$name.pid"
  local logfile="$LOGDIR/$name.log"
  if alive "$pidfile"; then
    echo "  $name already running pid=$(cat "$pidfile")"
    return 0
  fi
  nohup "$@" >>"$logfile" 2>&1 &
  echo $! >"$pidfile"
  echo "  started $name pid=$(cat "$pidfile") log=$logfile"
}

stop_one() {
  local name="$1"
  local pidfile="$PIDDIR/$name.pid"
  if ! alive "$pidfile"; then
    rm -f "$pidfile"
    echo "  $name not running"
    return 0
  fi
  local pid
  pid="$(cat "$pidfile")"
  kill "$pid" 2>/dev/null || true
  sleep 0.4
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$pidfile"
  echo "  stopped $name"
}

load_venv() {
  cd "$ROOT"
  # shellcheck disable=SC1090
  source "$VENV"
}

cmd="${1:-status}"
case "$cmd" in
  pull)
    cd "$ROOT"
    git checkout -- data/sol_day_latest_signal.json 2>/dev/null || true
    git pull --ff-only
    ;;
  lock)
    load_venv
    python scripts/formula_lock_agent.py --once
    ;;
  dash)
    load_venv
    stop_one dash
    start_one dash streamlit run demo/rsi_1m_dashboard.py --server.headless true --server.port 8501
    echo "  open http://localhost:8501"
    ;;
  up)
    cd "$ROOT"
    git checkout -- data/sol_day_latest_signal.json 2>/dev/null || true
    git pull --ff-only || true
    load_venv
    rm -f "$ROOT/data/KILL_SWITCH.txt"
    python scripts/formula_lock_agent.py --once || true
    start_one rsi1m python scripts/sol_1m_rsi_core_paper.py
    start_one solday python scripts/sol_day_autonomous_runner.py
    start_one lock python scripts/formula_lock_agent.py --poll 30
    start_one dash streamlit run demo/rsi_1m_dashboard.py --server.headless true --server.port 8501
    echo
    echo "Desk is up. Board: http://localhost:8501"
    echo "Stop with: ./scripts/desk.sh down"
    ;;
  down)
    stop_one dash
    stop_one lock
    stop_one rsi1m
    stop_one solday
    ;;
  status)
    echo "SOL desk @ $ROOT"
    for name in rsi1m solday lock dash; do
      if alive "$PIDDIR/$name.pid"; then
        echo "  $name RUNNING pid=$(cat "$PIDDIR/$name.pid")"
      else
        echo "  $name stopped"
      fi
    done
    echo "  board http://localhost:8501"
    if [[ -f "$ROOT/data/formula_lock_status.json" ]]; then
      python3 - "$ROOT/data/formula_lock_status.json" <<'PY'
import json,sys
st=json.load(open(sys.argv[1]))
print("  lock", "OK" if st.get("ok") else "DRIFT", "issues", st.get("issue_count"), "at", st.get("ts_utc"))
for i in st.get("issues") or []:
    print("   -", i)
PY
    fi
    ;;
  *)
    echo "usage: $0 up|down|status|pull|lock|dash"
    exit 1
    ;;
esac
