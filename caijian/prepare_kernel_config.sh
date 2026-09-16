#!/bin/bash
set -e
cd /tmp/openkylin-kernel
cp /tmp/qemu_env/openkylin-original.config .config
./scripts/config \
  --enable FTRACE \
  --enable KPROBES \
  --enable TRACEPOINTS \
  --enable EVENT_TRACING \
  --enable BPF_JIT \
  --enable BPF_EVENTS \
  --enable FTRACE_SYSCALLS \
  --enable DEBUG_INFO_BTF
./scripts/config --disable DEBUG_INFO_NONE --enable DEBUG_INFO --enable DEBUG_INFO_DWARF4
make ARCH=riscv olddefconfig
echo "=== 验证最终配置 ==="
grep -E "^CONFIG_FTRACE=|^CONFIG_KPROBES=|^CONFIG_BPF_JIT=|^CONFIG_DEBUG_INFO_BTF=|^CONFIG_TRACEPOINTS=" .config
echo "=== 版本确认(LOCALVERSION_AUTO应从git取后缀) ==="
grep -E "CONFIG_LOCALVERSION" .config
