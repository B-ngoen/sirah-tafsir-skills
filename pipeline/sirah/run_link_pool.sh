#!/usr/bin/env bash
# Pool 5 worker: tiap worker ambil batch berikutnya begitu selesai. Retry backoff bila hasil kosong.
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
mkdir -p data/link_results logs/link
one(){ b=$1; for try in 1 2 3 4; do
  [ -s "data/link_results/$b.json" ] && { echo "[$(date '+%T')] ok $b"; return 0; }
  pi --provider zai --model glm-5.3 -p --no-session "Baca data/LINK-LLM-SPEC.md, lalu kerjakan untuk batch $b: baca data/link_batches/$b.txt dan tulis data/link_results/$b.json" > "logs/link/${b}_r$try.out" 2>&1
  [ -s "data/link_results/$b.json" ] && { echo "[$(date '+%T')] ok $b (try $try)"; return 0; }
  sleep $((90*try)); done; echo "[$(date '+%T')] GAGAL $b"; return 1; }
export -f one
for f in data/link_batches/*.txt; do b=$(basename "$f" .txt); [ -s "data/link_results/$b.json" ] || echo "$b"; done | xargs -P 5 -I{} bash -c 'one {}'
echo "LINK BATCHES DONE: $(ls data/link_results/*.json 2>/dev/null | wc -l) hasil"
