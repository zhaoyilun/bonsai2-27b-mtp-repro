#!/bin/bash
# 用法: run_mtp_ab.sh <tag> <额外 llama-server 参数...>
set -u
TAG=$1; shift
MODEL=/home/zyl/models/Ternary-Bonsai-2-27B-PQ2_0-MTP-Q8_0.gguf
UNIT=bonsai-mtp-$TAG
LOG=/home/zyl/bonsai2/logs/mtp-$TAG.log
systemctl --user stop llama-bonsai.service 2>/dev/null
systemctl --user stop "$UNIT.service" 2>/dev/null
sleep 2
systemd-run --user --collect --unit="$UNIT" /bin/bash -c \
  "cd /home/zyl/bonsai2/mtp-runtime/source/llama/build/bin && LD_LIBRARY_PATH=/home/zyl/bonsai2/mtp-runtime/source/llama/build/bin HOME=/home/zyl \
   ./llama-server -m $MODEL -ngl 99 -fa on -c 131072 -ctk q4_0 -ctv q4_0 -np 1 \
   -t 16 --temp 0 --host 127.0.0.1 --port 8080 -a bonsai-mtp $* > $LOG 2>&1" 2>&1 | tail -1
for i in $(seq 1 60); do
  sleep 3
  curl -s --max-time 3 -o /dev/null http://127.0.0.1:8080/health 2>/dev/null && break
  systemctl --user is-active -q "$UNIT" || { echo "!! 单元退出，日志尾部："; tail -5 "$LOG"; exit 1; }
done
echo "== 服务就绪 (${TAG}) =="
grep -aiE "nextn|mtp|spec|draft" "$LOG" | head -5
python3 /home/zyl/bonsai2/mtp_bench.py 8080 "$TAG" 96
echo "== 服务端日志里的接受率行 =="
grep -a "draft acceptance" "$LOG" | tail -3
systemctl --user stop "$UNIT.service"
