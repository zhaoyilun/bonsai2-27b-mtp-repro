#!/bin/bash
set -u
B=/home/zyl/bonsai2/mtp-runtime/source/llama/build/bin
TAG=$1; shift
systemctl --user stop llama-bonsai-mtp.service 2>/dev/null; systemctl --user stop llama-bonsai.service 2>/dev/null
systemctl --user stop "mtpab-$TAG.service" 2>/dev/null; sleep 2
systemd-run --user --collect --unit="mtpab-$TAG" /bin/bash -c "cd $B && LD_LIBRARY_PATH=$B HOME=/home/zyl \
  ./llama-server -m /home/zyl/models/Ternary-Bonsai-2-27B-PQ2_0-MTP-Q8_0.gguf \
  -ngl 99 -fa on -c 262144 -ctk q4_0 -ctv q4_0 -np 1 -t 16 --temp 0 \
  --host 127.0.0.1 --port 8080 -a bonsai-mtp $* > /home/zyl/bonsai2/logs/ab-$TAG.log 2>&1" >/dev/null 2>&1
for i in $(seq 1 60); do sleep 3; curl -s --max-time 3 -o /dev/null http://127.0.0.1:8080/health 2>/dev/null && break; done
python3 /home/zyl/bonsai2/mtp_ab.py 8080 "$TAG" 128
systemctl --user stop "mtpab-$TAG.service"
