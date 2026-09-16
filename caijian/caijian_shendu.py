#!/usr/bin/env python3
import os
import pexpect, sys, time

logf = open("/tmp/qemu_env/caijian3.log", "w")
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

    mingling("dpkg -l | grep -E 'linux-image-6.6.110|linux-headers-6.6.110|vim-runtime|qttranslations' | wc -l", "#", 20)
    mingling("du -sh /lib/modules/*/ 2>/dev/null", "#", 30)
    mingling("cat /proc/modules | wc -l; lsmod | head -20", "#", 20)

    mingling("cd /lib/modules/6.6.129-g7ccea0cbe151/kernel && du -sh drivers net fs mm sound 2>/dev/null", "#", 40)

    mingling("journalctl --vacuum-size=10M 2>&1; rm -rf /var/log/journal/* 2>/dev/null; echo LOG_OK", "LOG_OK", 60)

    mingling("df -h / | tail -1; du -sh / 2>/dev/null | tail -1", "#", 30)
    mingling("echo CS3_DONE", "CS3_DONE", 15)
    child.sendline("poweroff -f")
    time.sleep(3)
    child.close()
except Exception as e:
    print("EXC:", e)
    child.close()
print(open("/tmp/qemu_env/caijian3.log").read()[-3500:])