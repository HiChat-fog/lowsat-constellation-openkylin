#!/usr/bin/env python3
import glob
import json
import os
import re
import secrets
import subprocess
import sys
import time

import socket
import pexpect

IP_MAP = {1: "192.168.50.1", 2: "192.168.50.2", 3: "192.168.50.3"}
DUANKOU_MAP = {1: 8011, 2: 8012, 3: 8013}
SHUJU = "/tmp/qemu_env/share/shuju"
GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIZHI = {}
MIYAO = os.environ.get("WX_MIYAO") or secrets.token_hex(16)
LING_PAI = os.environ.get("WX_LING_PAI") or secrets.token_hex(16)
DUAN_YAN = []


def jian_cha(ming, tiaojian, shuo_ming):
    DUAN_YAN.append((ming, bool(tiaojian), shuo_ming))
    zhuang = "通过" if tiaojian else "未过"
    print("[断言%s] %s" % (zhuang, shuo_ming), flush=True)
    return tiaojian


def deng_tiaojian(han_shu, miao, shuo_ming):
    jie_shu = time.time() + miao
    while time.time() < jie_shu:
        if han_shu():
            return True
        time.sleep(2)
    print("[断言超时] %s" % shuo_ming, flush=True)
    return False


def qidong(hao):
    rizhi = "/tmp/qemu_env/sx%d.log" % hao
    RIZHI[hao] = rizhi
    logf = open(rizhi, "w")
    child = pexpect.spawn(
        "qemu-system-riscv64 -machine virt -cpu max -display none -serial stdio "
        "-m 1024 -smp 2 "
        "-bios /usr/lib/riscv64-linux-gnu/opensbi/generic/fw_dynamic.bin "
        "-kernel /tmp/qemu_env/share/vmlinuz-zengqiang "
        "-append \"root=PARTUUID=d9eaf6f6-dcd6-45e1-b256-9212a47e393d ro earlycon console=ttyS0\" "
        "-drive file=xing%d.qcow2,format=qcow2,if=virtio "
        "-netdev user,id=wai,hostfwd=tcp:127.0.0.1:%d-:7947 "
        "-device virtio-net-pci,netdev=wai,mac=52:54:00:12:34:0%d "
        "-netdev tap,id=xingjian,ifname=xingtap%d,script=no,downscript=no "
        "-device virtio-net-pci,netdev=xingjian,mac=52:54:00:56:78:0%d "
        "-virtfs local,path=/tmp/qemu_env/share,mount_tag=hostshare,security_model=none"
        % (hao, DUANKOU_MAP[hao], hao, hao, hao),
        cwd="/tmp/qemu_env", encoding="utf-8", timeout=60)
    child.logfile = logf
    return child


def dengdai(child, s, t=90, biaozhi=""):
    try:
        child.expect(s, timeout=t)
        return True
    except pexpect.TIMEOUT:
        print("[%s] !! 超时: %s" % (biaozhi, s), flush=True)
        return False


def denglu(xing, hao):
    if not dengdai(xing, "login:", 150, "星%d" % hao):
        return False
    xing.sendline("root")
    dengdai(xing, "Password:", 20, "星%d" % hao)
    xing.sendline("openkylin")
    if not dengdai(xing, "#", 30, "星%d" % hao):
        return False
    time.sleep(1)
    xing.sendline("systemctl stop NetworkManager 2>/dev/null; ip link set enp0s2 up; ip addr flush dev enp0s2; ip addr add %s/24 dev enp0s2" % IP_MAP[hao])
    dengdai(xing, "#", 15, "星%d" % hao)
    time.sleep(1)
    xing.sendline("mount -t 9p -o trans=virtio hostshare /mnt/share 2>&1")
    dengdai(xing, "#", 20, "星%d" % hao)
    xing.sendline("systemctl stop xintiao.service agent.service jiance.service 2>/dev/null; "
                  "systemctl disable xintiao.service agent.service jiance.service 2>/dev/null; "
                  "pkill -f xingxin_riscv64 2>/dev/null; pkill -f agent_yonghu 2>/dev/null; echo FU_WU_YI_QING")
    dengdai(xing, "FU_WU_YI_QING", 25, "星%d" % hao)
    time.sleep(1)
    return True


def du_renwu_jieguo():
    print("--- 任务结果文件(宿主侧) ---", flush=True)
    for hao in [1, 2, 3]:
        lu = os.path.join(SHUJU, "renwu_weixing%d.json" % hao)
        if os.path.exists(lu):
            with open(lu) as f:
                hang = f.read().strip().splitlines()
            for h in hang[-2:]:
                print("  weixing%d: %s" % (hao, h), flush=True)


def you_renwu_jieguo():
    return glob.glob(os.path.join(SHUJU, "renwu_*.json")) != []


def you_jieguan():
    for lu in glob.glob(os.path.join(SHUJU, "renwu_*.json")):
        try:
            with open(lu) as f:
                if "JIEGUAN" in f.read():
                    return True
        except Exception:
            pass
    return "JIEGUAN" in du_diaodu_ri() or "云端迁移" in du_diaodu_ri()


def xin_yao(hao, guanjian_ci):
    try:
        with open("/tmp/qemu_env/sx%d.log" % hao) as f:
            return guanjian_ci in f.read()
    except Exception:
        return False


def du_diaodu_ri():
    try:
        with open("/tmp/qemu_env/diaodu.log") as f:
            return f.read()
    except Exception:
        return ""


def fa_chang_renwu(hao):
    for _ in range(3):
        try:
            s = socket.create_connection(("127.0.0.1", DUANKOU_MAP[hao]), timeout=5)
            bao = {"mingling": "PAIFA", "ling_pai": LING_PAI,
                   "renwu": {"bianhao": "rw-changqi", "ming": "zai_gui_chu_li",
                             "canliang": 3000000, "chang_shi": 1}}
            s.sendall((json.dumps(bao) + "\n").encode())
            hui = s.recv(128).decode()
            s.close()
            jie = json.loads(hui)
            if "OK" in jie.get("jieguo", ""):
                return jie
            print("[chang_renwu] hui_fu=%s chong_shi" % hui.strip(), flush=True)
        except Exception as cuo:
            print("[chang_renwu] yi_chang=%s chong_shi" % cuo, flush=True)
        time.sleep(2)
    return None


def pai_dao_le(xingming):
    return re.search(r"派发\|rw-\d+\|%s" % xingming, du_diaodu_ri()) is not None


xings = {}
diaodu_guocheng = None
try:
    t0 = time.time()
    for hao in [1, 2, 3]:
        xings[hao] = qidong(hao)
    print("=== 三星并行启动 ===", flush=True)
    for hao in [1, 2, 3]:
        denglu(xings[hao], hao)
    print("=== 三星就绪,耗时 %ds ===" % (time.time() - t0), flush=True)
    time.sleep(2)

    print("=== 每星启动观测 agent ===", flush=True)
    for hao in [1, 2, 3]:
        xings[hao].sendline("mkdir -p /mnt/share/shuju; /mnt/share/agent_yonghu weixing%d 3 /mnt/share/shuju > /mnt/share/shuju/weixing%d.json &" % (hao, hao))
        time.sleep(2)
    time.sleep(6)

    deng_tiaojian(lambda: all(os.path.exists(os.path.join(SHUJU, "weixing%d.json" % h)) for h in [1, 2, 3]), 90, "三星遥测文件就绪")
    jian_cha("yaogce", all(os.path.exists(os.path.join(SHUJU, "weixing%d.json" % h)) for h in [1, 2, 3]), "三星遥测经9p实时落盘")
    jian_cha("sqlite", deng_tiaojian(lambda: all(os.path.exists(os.path.join(SHUJU, "weixing%d.db" % h)) for h in [1, 2, 3]), 30, "三星SQLite库就绪"), "三星SQLite库落盘于共享目录(云端可读)")

    print("=== 心跳组网(含任务执行器) ===", flush=True)
    xings[1].sendline("WX_MIYAO=%s WX_LING_PAI=%s /mnt/share/xingxin_riscv64 weixing1 7946 192.168.50.1 > /tmp/xin1.txt 2>&1 &" % (MIYAO, LING_PAI))
    time.sleep(3)
    xings[2].sendline("WX_MIYAO=%s WX_LING_PAI=%s /mnt/share/xingxin_riscv64 weixing2 7946 192.168.50.2 192.168.50.1:7946 > /tmp/xin2.txt 2>&1 &" % (MIYAO, LING_PAI))
    time.sleep(3)
    xings[3].sendline("WX_MIYAO=%s WX_LING_PAI=%s /mnt/share/xingxin_riscv64 weixing3 7946 192.168.50.3 192.168.50.1:7946 > /tmp/xin3.txt 2>&1 &" % (MIYAO, LING_PAI))
    time.sleep(20)
    for hao in (1, 2, 3):
        xings[hao].sendline("cp /tmp/xin%d.txt /mnt/share/shuju/xin%d_kuaizhao.txt" % (hao, hao))
        dengdai(xings[hao], "#", 10, "星%d" % hao)
    time.sleep(2)

    def xin_kuai(hao):
        try:
            with open("/tmp/qemu_env/share/shuju/xin%d_kuaizhao.txt" % hao) as f:
                return f.read()
        except Exception:
            return ""

    jian_cha("zuneng", "成功加入集群" in xin_kuai(2) and "成功加入集群" in xin_kuai(3), "星2/星3心跳组网成功")
    print("--- 星1 组网日志尾部 ---", flush=True)
    print(xin_kuai(1)[-300:], flush=True)

    print("=== 启动云端调度器(真实 TCP 派发) ===", flush=True)
    diaodu_log = open("/tmp/qemu_env/diaodu.log", "w", buffering=1)
    diaodu_guocheng = subprocess.Popen(
        [sys.executable, os.path.join(GEN, "mianban", "diaodu_yun.py")],
        stdout=diaodu_log, stderr=subprocess.STDOUT,
        env=dict(os.environ, WX_LING_PAI=LING_PAI))
    jian_cha("paifa", deng_tiaojian(lambda: "派发|" in du_diaodu_ri(), 60, "云端派发"), "云端调度器真实TCP派发任务")
    jian_cha("jieguo", deng_tiaojian(you_renwu_jieguo, 120, "任务结果回传"), "任务结果经星上执行后回传云端")

    print("\n=== 等待任务派发到星2,注入长任务与故障 %s ===" % time.strftime("%H:%M:%S"), flush=True)
    deng_tiaojian(lambda: pai_dao_le("weixing2"), 120, "任务派发到星2")
    du_renwu_jieguo()
    chang_hui = fa_chang_renwu(2)
    jian_cha("chang_renwu", bool(chang_hui and "OK" in chang_hui.get("jieguo", "")), "长任务派到星2执行中")
    time.sleep(1)
    xings[2].sendline("pkill -9 -x xingxin_riscv64")
    dengdai(xings[2], "#", 10, "星2")
    jiage = time.time()
    time.sleep(25)

    jian_cha("jiegguan", deng_tiaojian(you_jieguan, 60, "星间接管/云端迁移证据"), "单节点故障后任务60秒内迁移或恢复")
    for hao in (1, 3):
        xings[hao].sendline("cp /tmp/xin%d.txt /mnt/share/shuju/xin%d_jieguan.txt" % (hao, hao))
        dengdai(xings[hao], "#", 10, "星%d" % hao)
    time.sleep(2)
    print("--- 星1 接管日志 ---", flush=True)
    try:
        with open("/tmp/qemu_env/share/shuju/xin1_jieguan.txt") as f:
            print("\n".join([x for x in f.read().splitlines()
                             if "离开" in x or "接管" in x or "RENWU" in x or "转派" in x][-8:]), flush=True)
    except Exception:
        print("wu ri zhi", flush=True)
    du_renwu_jieguo()
    print("--- 云端调度器日志(故障后) ---", flush=True)
    print(du_diaodu_ri()[-800:], flush=True)

    print("\n=== 星2 恢复重入 %s(故障后%.0f秒) ===" % (time.strftime("%H:%M:%S"), time.time() - jiage), flush=True)
    xings[2].sendline("WX_MIYAO=%s WX_LING_PAI=%s /mnt/share/xingxin_riscv64 weixing2 7946 192.168.50.2 192.168.50.1:7946 > /tmp/xin2b.txt 2>&1 &" % (MIYAO, LING_PAI))
    time.sleep(12)
    xings[1].sendline("tail -2 /tmp/xin1.txt")
    dengdai(xings[1], "#", 10, "星1")
    time.sleep(2)
    du_renwu_jieguo()
    print("--- 云端调度器日志(收尾) ---", flush=True)
    print(du_diaodu_ri()[-500:], flush=True)

    print("\n=== 演示完成,总耗时 %ds ===" % (time.time() - t0), flush=True)
    for hao in [1, 2, 3]:
        xings[hao].sendline("poweroff -f")
    time.sleep(4)
    for hao in [1, 2, 3]:
        xings[hao].close()
except Exception as e:
    print("EXC:", e)
    for hao, x in xings.items():
        try:
            x.close()
        except:
            pass
finally:
    if diaodu_guocheng:
        diaodu_guocheng.terminate()

print("\n=== 断言汇总 ===", flush=True)
tong_guo = 0
for ming, hao, shuo in DUAN_YAN:
    print("[%s] %s: %s" % ("通过" if hao else "未过", ming, shuo), flush=True)
    if hao:
        tong_guo += 1
print("断言 %d/%d 通过" % (tong_guo, len(DUAN_YAN)), flush=True)
sys.exit(0 if tong_guo == len(DUAN_YAN) and DUAN_YAN else 1)
