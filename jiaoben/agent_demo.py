#!/usr/bin/env python3
import pexpect, sys, time

logf = open("/tmp/qemu_env/agent_demo.log", "w")
child = pexpect.spawn(
    "qemu-system-riscv64 -machine virt -cpu max -display none -serial stdio "
    "-m 4096 -smp 4 "
    "-bios /usr/lib/riscv64-linux-gnu/opensbi/generic/fw_dynamic.bin "
    "-kernel /usr/lib/u-boot/qemu-riscv64_smode/uboot.elf "
    "-drive file=/tmp/openkylin-2.0-sp2-rc1-qemu-rva23.img,format=raw,if=virtio "
    "-virtfs local,path=/tmp/qemu_env/share,mount_tag=hostshare,security_model=none",
    encoding="utf-8", timeout=60)
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
    dengdai("Hit any key to stop autoboot", 60)
    child.sendline(""); time.sleep(1)
    dengdai("=>", 15)
    child.sendline("setenv fdt_high 0"); time.sleep(1)
    child.sendline("run distro_bootcmd")
    dengdai("(Booting|openKylin|[Ll]inux)", 30)
    idx = child.expect(["maintenance", "login:", pexpect.TIMEOUT], timeout=150)
    if idx == 1:
        child.sendline("root"); dengdai("Password:", 20); child.sendline("openkylin")
    else:
        dengdai("Give root password", 15); child.sendline("openkylin")
    dengdai("#", 30)
    mingling("mount -t 9p -o trans=virtio hostshare /mnt/share 2>&1", "#", 20)

    child.sendline("/mnt/share/agent_yonghu weixing1 3 > /tmp/agent_out.txt 2>&1 &")
    time.sleep(3)
    mingling("ls -la /usr/bin > /dev/null; find /usr -name '*.conf' > /dev/null 2>&1", "#", 25)
    time.sleep(6)
    mingling("for i in 1 2 3 4 5; do find / -name '*.so' 2>/dev/null > /dev/null; done", "#", 25)
    time.sleep(3)
    mingling("sha256sum /usr/bin/* > /dev/null 2>&1 & sha256sum /usr/lib/*.so* > /dev/null 2>&1 &", "#", 10)
    time.sleep(8)
    child.sendline("echo AGENT_STOP; kill %1")
    dengdai("AGENT_STOP", 15)
    time.sleep(2)
    child.sendline("cat /tmp/agent_out.txt")
    dengdai("#", 15)
    time.sleep(2)
    mingling("echo AGENT_DEMO_DONE", "AGENT_DEMO_DONE", 15)
    child.sendline("sync; poweroff -f")
    time.sleep(4)
    child.close()
except Exception as e:
    print("EXC:", e)
    child.close()

print(open("/tmp/qemu_env/agent_demo.log").read()[-8000:])