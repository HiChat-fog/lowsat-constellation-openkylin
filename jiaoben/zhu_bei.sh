#!/bin/bash
set -e

GEN="$(cd "$(dirname "$0")/.." && pwd)"
CS="$(dirname "$GEN")"
SHIYAN="$CS/shiyan"
YUN_XING=/tmp/qemu_env
JI_XIAN="$SHIYAN/镜像/openkylin-2.0-sp2-rc1-qemu-rva23.img"

wang_luo() {
    ip link add xingqiao type bridge 2>/dev/null || true
    ip link set xingqiao up 2>/dev/null || true
    for i in 1 2 3; do
        ip tuntap add dev "xingtap$i" mode tap user "${SUDO_USER:-$(whoami)}" 2>/dev/null || true
        ip link set "xingtap$i" master xingqiao 2>/dev/null || true
        ip link set "xingtap$i" up 2>/dev/null || true
    done
    echo "WANG_LUO_JIU_XU"
}

if [ "$1" = "wang_luo" ]; then
    wang_luo
    exit 0
fi

if sudo -n true 2>/dev/null; then
    sudo -n bash "$0" wang_luo
else
    echo "qing shu ru sudo mi ma:"
    sudo -S -p '' bash "$0" wang_luo
fi

pkill -f qemu-system 2>/dev/null || true
sleep 1

mkdir -p "$YUN_XING"
for i in 1 2 3; do
    [ -f "$YUN_XING/xing$i.qcow2" ] || cp "$SHIYAN/qemu_env/xing$i.qcow2" "$YUN_XING/"
done
[ -d "$YUN_XING/share" ] || cp -r "$SHIYAN/qemu_env/share" "$YUN_XING/"
if [ ! -f "$GEN/chengwu/agent_yonghu" ] || [ ! -f "$GEN/chengwu/xingxin_riscv64" ]; then
    make -C "$GEN" all
fi
cp "$GEN/chengwu/agent_yonghu" "$GEN/chengwu/xingxin_riscv64" \
   "$GEN/chengwu/jiance" "$GEN/chengwu/jiankang" "$GEN/chengwu/dianyuan" "$YUN_XING/share/"
chmod +x "$YUN_XING/share/agent_yonghu" "$YUN_XING/share/xingxin_riscv64" \
         "$YUN_XING/share/jiance" "$YUN_XING/share/jiankang"
if [ -f "$GEN/jiaoben/dianyuan_jiankang.sh" ]; then
    cp "$GEN/jiaoben/dianyuan_jiankang.sh" "$YUN_XING/share/"
fi
rm -f "$YUN_XING/share/shuju/"*.json "$YUN_XING/share/shuju/"*.db \
      "$YUN_XING/share/shuju/"*.shijian "$YUN_XING/share/shuju/"*.txt 2>/dev/null || true

if [ ! -e /tmp/openkylin-2.0-sp2-rc1-qemu-rva23.img ]; then
    ln -s "$JI_XIAN" /tmp/openkylin-2.0-sp2-rc1-qemu-rva23.img
fi
if [ ! -e /tmp/openkylin-kernel ] && [ -d "$SHIYAN/openkylin-kernel" ]; then
    ln -s "$SHIYAN/openkylin-kernel" /tmp/openkylin-kernel
fi

command -v qemu-system-riscv64 >/dev/null || { echo "que shao qemu-system-riscv64"; exit 1; }
[ -f "$YUN_XING/share/vmlinuz-zengqiang" ] || { echo "que shao nei he vmlinuz-zengqiang"; exit 1; }
for i in 1 2 3; do
    [ -f "$YUN_XING/xing$i.qcow2" ] || { echo "que shao xing$i.qcow2"; exit 1; }
    ip link show "xingtap$i" >/dev/null || { echo "que shao xingtap$i"; exit 1; }
done

echo "=== HUAN_JING_JIU_XU: $YUN_XING ==="
ip -br link | grep -E "xingqiao|xingtap"
