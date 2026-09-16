#!/bin/sh
MO_REN=$(find /mnt/share/shuju -maxdepth 1 -name 'weixing*.json' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
WEN=${1:-$MO_REN}
if [ ! -f "$WEN" ]; then
    echo '{"pan_ding":"wu_shu_ju"}'
    exit 0
fi
HANG=$(grep '^{' "$WEN" | tail -1)
CPU=$(printf '%s' "$HANG" | grep -o '"cpu":[0-9.]*' | cut -d: -f2)
NEI=$(printf '%s' "$HANG" | grep -o '"neicun":[0-9]*' | cut -d: -f2)
if [ -z "$CPU" ] || [ -z "$NEI" ]; then
    echo "{\"pan_ding\":\"ge_shi_yi\",\"wen\":\"$WEN\"}"
    exit 0
fi
GAO=$(awk -v a="$CPU" -v b="$NEI" 'BEGIN{print (a>85||b>85)?"gao_zai":"zheng_chang"}')
echo "{\"pan_ding\":\"$GAO\",\"cpu\":$CPU,\"neicun\":$NEI,\"wen\":\"$WEN\"}"
