#!/bin/sh
# Job-discovery web UI — one command to run it, stop it, or check on it.
#
#   ./start.sh          # start the UI (opens the browser)
#   ./start.sh stop     # stop the running UI
#   ./start.sh status   # is it running?
#
# Port comes from config.toml ([run].web_port, env WEB_PORT overrides).
set -e
cd "$(dirname "$0")"

PORT=$(python3 -c "import discover_jobs as d; print(d.WEB_PORT)")
PID=$(lsof -tnP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)

case "${1:-start}" in
  stop)
    if [ -n "$PID" ]; then
      kill "$PID" && echo "Stopped (pid $PID, port $PORT)."
    else
      echo "Not running (nothing listening on port $PORT)."
    fi
    ;;
  status)
    if [ -n "$PID" ]; then
      echo "Running (pid $PID) — http://localhost:$PORT"
    else
      echo "Not running."
    fi
    ;;
  start)
    if [ -n "$PID" ]; then
      echo "Already running (pid $PID) — http://localhost:$PORT"
      echo "Use './start.sh stop' to stop it first."
      exit 0
    fi
    echo "Starting the UI at http://localhost:$PORT ..."
    # CSV mode still available directly: python3 discover_jobs.py  (no --web flag)
    ( sleep 2 && open "http://localhost:$PORT" ) 2>/dev/null &
    exec python3 discover_jobs.py --web
    ;;
  *)
    echo "Usage: ./start.sh [start|stop|status]"
    exit 1
    ;;
esac
