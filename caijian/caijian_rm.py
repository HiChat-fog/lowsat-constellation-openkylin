#!/usr/bin/env python3
import os
import pexpect, sys, time

logf = open("/tmp/qemu_env/cj4.log", "w")
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

    print("=== 裁剪前 ===", flush=True)
    mingling("df -h / | tail -1", "#", 20)

    mingling("cd /lib/modules/6.6.129-g7ccea0cbe151/kernel && rm -rf drivers net arch crypto lib sound mm ipc security 2>&1; echo RM1_OK", "RM1_OK", 120)
    mingling("cd /lib/modules/6.6.129-g7ccea0cbe151/kernel && rm -rf fs/* && ls fs/nls 2>/dev/null || mkdir -p fs/nls", "RM2", 60)
    mingling("find /lib/modules/6.6.129-g7ccea0cbe151/kernel -type f | head -5", "#", 30)
    mingling("ls /lib/modules/6.6.129-g7ccea0cbe151/kernel/fs/nls/ 2>&1", "#", 20)
    mingling("ls /lib/modules/6.6.129-g7ccea0cbe151/kernel/fs/nls/nls_iso8859-1.ko 2>&1", "#", 15)

    mingling("depmod -a 2>&1; echo DEPMOD_OK", "DEPMOD_OK", 120)

    mingling("rm -f /etc/modules-load.d/*.conf 2>/dev/null; echo MODS_OK", "MODS_OK", 30)

    print("=== 裁剪后 ===", flush=True)
    mingling("df -h / | tail -1; du -sh /lib/modules/ 2>/dev/null", "#", 30)

    mingling("echo CJ4_DONE", "CJ4_DONE", 15)
    child.sendline("sync; poweroff -f")
    time.sleep(4)
    child.close()
except Exception as e:
    print("EXC:", e)
    child.close()
print(open("/tmp/qemu_env/cj4.log").read()[-3500:])