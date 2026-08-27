#!/usr/bin/env bash
# Loop fetch sampai flag selesai; aman di-restart. Dipanggil dalam tmux:
#   SIRAH_PARTITION=vps2 bash run_loop.sh
set -u
cd "$(dirname "$0")"
PART="${SIRAH_PARTITION:-all}"
mkdir -p data logs
exec 9>"logs/fetch_${PART}.lock"
flock -n 9 || { echo "sudah jalan (lock)"; exit 0; }
while [ ! -f "data/fetch_done_${PART}.flag" ]; do
  SIRAH_PARTITION="$PART" SIRAH_MAX_RUNTIME="${SIRAH_MAX_RUNTIME:-14400}" python3 fetch_sirah.py
  [ -f "data/fetch_done_${PART}.flag" ] && break
  sleep 30
done
echo "[$(date '+%F %T')] LOOP SELESAI [$PART]" | tee -a logs/fetch_sirah.log
