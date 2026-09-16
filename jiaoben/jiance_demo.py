#!/usr/bin/env python3
import pexpect, sys, time

logf = open("/tmp/qemu_env/jiance_demo.log", "w")
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

    child.sendline("/mnt/share/agent_yonghu weixing1 3 > /tmp/ag.txt 2>&1 &")
    mingling("/mnt/share/jiance weixing1 > /tmp/jc.txt 2>&1 &", "#", 10)
    time.sleep(16)
    child.sendline("echo BOOM; cat /tmp/jc.txt")
    dengdai("监测结束", 10)
    time.sleep(1)
    child.sendline("echo ===AGENT===")
    dengdai("===", 10)
    child.sendline("cat /tmp/ag.txt")
    dengdai("#", 10)
    time.sleep(1)
    mingling("echo JIANCE_DONE", "JIANCE_DONE", 15)
    child.sendline("sync; poweroff -f")
    time.sleep(4)
    child.close()
except Exception as e:
    print("EXC:", e)
    child.close()

print(open("/tmp/qemu_env/jiance_demo.log").read()[-7000:])