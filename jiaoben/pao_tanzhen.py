#!/usr/bin/env python3
import pexpect, sys, time

tanzhen = sys.argv[1] if len(sys.argv) > 1 else "caiji_yonghu"
miao = sys.argv[2] if len(sys.argv) > 2 else "20"
fuza = sys.argv[3] if len(sys.argv) > 3 else "ls -la /usr/bin > /dev/null; find /usr/share -name '*.conf' 2>/dev/null > /dev/null; cat /proc/meminfo > /dev/null; grep -r 'a' /etc 2>/dev/null > /dev/null"

logf = open("/tmp/qemu_env/pao_tanzhen.log", "w")
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
        print("[ok] %s" % s, flush=True)
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
    if not dengdai("Hit any key to stop autoboot", 60): sys.exit("无 autoboot")
    child.sendline(""); time.sleep(1)
    if not dengdai("=>", 15): sys.exit("无提示符")
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
    child.sendline("/mnt/share/%s %s > /tmp/tanzhen_out.txt 2>&1 &" % (tanzhen, miao))
    time.sleep(2)
    mingling(fuza, "#", 30)
    child.sendline("wait; sleep 1")
    time.sleep(int(miao) + 8)
    child.sendline("cat /tmp/tanzhen_out.txt")
    dengdai("#", 15)
    time.sleep(2)
    mingling("echo TANZHEN_DONE", "TANZHEN_DONE", 15)
    child.sendline("sync; poweroff -f")
    time.sleep(4)
    child.close()
except Exception as e:
    print("EXC:", e)
    child.close()

print(open("/tmp/qemu_env/pao_tanzhen.log").read()[-7000:])