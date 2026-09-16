#!/usr/bin/env python3
import os
import pexpect, sys, time

logf = open("/tmp/qemu_env/caijian_mem.log", "w")
child = pexpect.spawn(
    "qemu-system-riscv64 -machine virt -cpu max -display none -serial stdio "
    "-m 2048 -smp 2 "
    "-bios /usr/lib/riscv64-linux-gnu/opensbi/generic/fw_dynamic.bin "
    "-kernel /tmp/qemu_env/share/vmlinuz-zengqiang "
    "-append \"root=PARTUUID=d9eaf6f6-dcd6-45e1-b256-9212a47e393d ro earlycon console=ttyS0\" "
    "-drive file=%s,format=qcow2,if=virtio " % (os.environ.get("WX_QCOW2", "xing3") + ".qcow2") +
    "-netdev user,id=wai -device virtio-net-pci,netdev=wai,mac=52:54:00:12:34:03 "
    "-virtfs local,path=/tmp/qemu_env/share,mount_tag=hostshare,security_model=none",
    cwd="/tmp/qemu_env", encoding="utf-8", timeout=60)
child.logfile = logf

def dengdai(s, t=90):
    try:
        child.expect(s, timeout=t)
        return True
    except pexpect.TIMEOUT:
        print("[!!] 超时: %s" % s, flush=True)
        return False

def mingling(cmd, tag="#", t=60):
    child.sendline(cmd)
    r = dengdai(tag, t)
    time.sleep(0.5)
    return r

try:
    dengdai("login:", 150)
    child.sendline("root")
    dengdai("Password:", 20)
    child.sendline("openkylin")
    dengdai("#", 40)
    time.sleep(30)
    mingling("free -m | head -2", "#", 15)
    mingling("cat /proc/meminfo | head -3", "#", 15)
    mingling("echo CJ_MEM_DONE", "CJ_MEM_DONE", 15)
    child.sendline("sync; poweroff")
    time.sleep(4)
    child.close()
except Exception as e:
    print("EXC:", e)
    child.close()
print("裁剪后内存测量日志:")
print(open("/tmp/qemu_env/caijian_mem.log").read()[-1200:])