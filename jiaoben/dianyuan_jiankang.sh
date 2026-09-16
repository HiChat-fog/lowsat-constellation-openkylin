#!/bin/sh
RI=${1:-/mnt/share/shuju}
WEN=$(find "$RI" -maxdepth 1 -name '*.dianyuan' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
if [ -z "$WEN" ] || [ ! -f "$WEN" ]; then
    echo '{"pan_duan":"wu_shu_ju"}'
    exit 0
fi
HANG=$(grep '^REPORT|' "$WEN" | tail -1)
if [ -z "$HANG" ]; then
    echo "{\"pan_duan\":\"ge_shi_yi\",\"wen\":\"$WEN\"}"
    exit 0
fi
SOH=$(printf '%s' "$HANG" | grep -o 'soh=[0-9.]*' | cut -d= -f2)
RUL=$(printf '%s' "$HANG" | grep -o 'rul=[-0-9.]*' | cut -d= -f2)
SOC=$(printf '%s' "$HANG" | grep -o 'soc=[0-9.]*' | cut -d= -f2)
BAO=$(grep -c '^ALARM|' "$WEN")
PAN=zheng_chang
if [ -n "$SOH" ] && [ -n "$RUL" ]; then
    PAN=$(awk -v s="$SOH" -v r="$RUL" 'BEGIN{print (s<70||r<5)?"xu_yao_guan_zhu":"jian_kang"}')
fi
if [ "$BAO" -gt 0 ]; then
    JIN=$(grep '^ALARM|' "$WEN" | tail -1 | cut -d'|' -f6)
    PAN="$PAN|$JIN"
fi
printf '{"pan_duan":"%s","soh":%s,"rul":%s,"soc":%s,"bao_jing_shu":%s,"wen":"%s"}\n' \
    "$PAN" "${SOH:-null}" "${RUL:-null}" "${SOC:-null}" "$BAO" "$WEN"
