#!/bin/bash
X=/tmp/reuse/xingxin/xingxin_amd64

pkill -9 -x xingxin_amd64 2>/dev/null
sleep 1

$X xingA 7946 > /tmp/xa2.log 2>&1 &
AP=$!
$X xingB 7947 127.0.0.1:7946 > /tmp/xb2.log 2>&1 &
BP=$!
sleep 8
echo "=== $(date +%H:%M:%S) 杀A模拟卫星故障 ==="
kill -9 $AP 2>/dev/null
sleep 14
echo "=== B节点检测结果 ==="
grep -E "离开|成员" /tmp/xb2.log | tail -5
kill $BP 2>/dev/null
echo wan_bi