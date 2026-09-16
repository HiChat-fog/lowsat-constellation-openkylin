#!/usr/bin/env python3
import pexpect, sys, time

logf = open("/tmp/qemu_env/wulei_demo.log", "w")
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
    mingling("mkdir -p /tmp/cc && cp /mnt/share/*_yonghu /mnt/share/jiankang /tmp/cc/ && chmod +x /tmp/cc/* && ls /tmp/cc/", "#", 30)

    donghua = "dd if=/dev/zero of=/tmp/w.bin bs=1k count=4096 2>/dev/null; cat /tmp/w.bin > /dev/null; rm /tmp/w.bin; find /usr -name '*.conf' 2>/dev/null > /dev/null"

    print("\n########## 第一类 应用任务 ##########", flush=True)
    child.sendline("/tmp/cc/caiji_yonghu 15 > /tmp/cc/1.txt 2>&1 &")
    time.sleep(2)
    mingling(donghua, "#", 30)
    child.sendline("wait; sleep 1")
    time.sleep(18)
    child.sendline("cat /tmp/cc/1.txt")
    dengdai("#", 15); time.sleep(2)

    print("\n########## 第二类 系统资源 ##########", flush=True)
    child.sendline("/tmp/cc/ziyuan_yonghu 15 > /tmp/cc/2.txt 2>&1 &")
    time.sleep(2)
    mingling(donghua, "#", 30)
    child.sendline("wait; sleep 1")
    time.sleep(18)
    child.sendline("cat /tmp/cc/2.txt")
    dengdai("#", 15); time.sleep(2)

    print("\n########## 第三类 异构算力 ##########", flush=True)
    child.sendline("/tmp/cc/suanli_yonghu 15 > /tmp/cc/3.txt 2>&1 &")
    time.sleep(2)
    mingling("for i in 1 2 3 4; do sha256sum /usr/bin/* > /dev/null 2>&1 & done; sleep 1", "#", 30)
    mingling("sha256sum /usr/lib/*.so* > /dev/null 2>&1", "#", 30)
    child.sendline("wait; sleep 1")
    time.sleep(18)
    child.sendline("cat /tmp/cc/3.txt")
    dengdai("#", 15); time.sleep(2)

    print("\n########## 第四五类 功耗温度/节点健康 ##########", flush=True)
    mingling("/tmp/cc/jiankang", "#", 15)
    time.sleep(1)

    mingling("echo WULEI_DEMO_DONE", "WULEI_DEMO_DONE", 15)
    child.sendline("sync; poweroff -f")
    time.sleep(4)
    child.close()
except Exception as e:
    print("EXC:", e)
    child.close()

print(open("/tmp/qemu_env/wulei_demo.log").read()[-6000:])