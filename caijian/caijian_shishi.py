#!/usr/bin/env python3
import os
import pexpect, sys, time

logf = open("/tmp/qemu_env/caijian2.log", "w")
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

    print("=== 裁剪前基线 ===", flush=True)
    mingling("df -h / | tail -1; free -m | head -2", "#", 20)

    print("=== 卸载旧内核+开发/桌面无关组件 ===", flush=True)
    mingling("apt-get remove -y --purge linux-image-6.6.110-g89f7b81a4b04 linux-headers-6.6.110-g89f7b81a4b04 2>&1 | tail -2", "#", 300)
    mingling("apt-get remove -y --purge vim vim-runtime vim-common vim-tiny 2>&1 | tail -2", "#", 120)
    mingling("apt-get remove -y --purge qttranslations5-l10n qt5-qmake qtbase5-dev 2>&1 | tail -2", "#", 120)
    mingling("apt-get remove -y --purge binutils-riscv64-linux-gnu binutils-common binutils 2>&1 | tail -2", "#", 120)
    mingling("apt-get remove -y --purge linux-libc-dev 2>&1 | tail -2", "#", 120)
    mingling("apt-get remove -y --purge manpages manpages-dev 2>&1 | tail -2", "#", 120)
    mingling("apt-get autoremove -y 2>&1 | tail -2", "#", 180)
    mingling("apt-get clean 2>&1; rm -rf /var/lib/apt/lists/* /var/cache/apt/* 2>/dev/null", "#", 60)
    mingling("rm -rf /usr/share/doc/* /usr/share/man/* /usr/share/info/* 2>/dev/null; echo QINGLI_OK", "QINGLI_OK", 120)

    print("=== 裁剪后 ===", flush=True)
    mingling("df -h / | tail -1; free -m | head -2", "#", 20)
    mingling("du -sh / 2>/dev/null | tail -1", "#", 30)

    mingling("echo CAIJIAN_DONE", "CAIJIAN_DONE", 15)
    child.sendline("poweroff -f")
    time.sleep(3)
    child.close()
except Exception as e:
    print("EXC:", e)
    child.close()
print(open("/tmp/qemu_env/caijian2.log").read()[-4000:])