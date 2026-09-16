#!/usr/bin/env python3
"""三星常驻实验平台:拉起三台 QEMU 星(观测 agent + 星间心跳),供 A/B 调度、
故障注入、开销基准等实验复用。心跳日志直写共享目录(宿主可实时读),密钥落盘。
启动后监听 127.0.0.1:8029,接受 JSON 单行指令控制星上串口:
    {"cmd":"run","hao":2,"line":"pkill -x xingxin_riscv64; echo MARK","expect":"MARK","timeout":20}
    {"cmd":"send","hao":2,"line":"..."}                 # 只发不等
    {"cmd":"rejoin","hao":2}                            # 星2 重拉 xingxin(默认参数)
    {"cmd":"rejoin_all","env":{"WX_SUSPICION_MULT":"3"}}# 全体重拉 xingxin(附加 env)
    {"cmd":"guanbi"}                                    # 关闭三星
    {"cmd":"ping"}
回应单行 JSON:{"ok":true,"before":"..."} / {"ok":false,"cuo":"..."}

用法:
    python3 shiyan_pingtai.py --qidong    # 拉起并驻留(前台,含控制端口)
    python3 shiyan_pingtai.py --zhuangtai # 查看平台状态(不阻塞)
    python3 shiyan_pingtai.py --guanbi    # 关闭三星
"""
import json
import os
import secrets
import socketserver
import subprocess
import sys
import threading
import time

import pexpect

IP_MAP = {1: "192.168.50.1", 2: "192.168.50.2", 3: "192.168.50.3"}
DUANKOU_MAP = {1: 8011, 2: 8012, 3: 8013}
SHUJU = "/tmp/qemu_env/share/shuju"
GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YUN = "/tmp/qemu_env"
KONG_ZHI_DUAN = 8029
MIAO = os.path.join(YUN, "shiyan_miyao.json")
XINGS = {}
SUO = threading.Lock()


def qidong(hao):
    rizhi = os.path.join(YUN, "sx%d.log" % hao)
    logf = open(rizhi, "w")
    child = pexpect.spawn(
        "qemu-system-riscv64 -machine virt -cpu max -display none -serial stdio "
        "-m 1024 -smp 2 "
        "-bios /usr/lib/riscv64-linux-gnu/opensbi/generic/fw_dynamic.bin "
        "-kernel %s/share/vmlinuz-zengqiang " % YUN +
        "-append \"root=PARTUUID=d9eaf6f6-dcd6-45e1-b256-9212a47e393d ro earlycon console=ttyS0\" "
        "-drive file=xing%d.qcow2,format=qcow2,if=virtio "
        "-netdev user,id=wai,hostfwd=tcp:127.0.0.1:%d-:7947 "
        "-device virtio-net-pci,netdev=wai,mac=52:54:00:12:34:0%d "
        "-netdev tap,id=xingjian,ifname=xingtap%d,script=no,downscript=no "
        "-device virtio-net-pci,netdev=xingjian,mac=52:54:00:56:78:0%d "
        "-virtfs local,path=%s/share,mount_tag=hostshare,security_model=none"
        % (hao, DUANKOU_MAP[hao], hao, hao, hao, YUN),
        cwd=YUN, encoding="utf-8", timeout=60)
    child.logfile = logf
    return child


def dengdai(xing, s, t=90, biaozhi=""):
    try:
        xing.expect(s, timeout=t)
        return True
    except pexpect.TIMEOUT:
        print("[%s] !! 超时: %s" % (biaozhi, s), flush=True)
        return False


def denglu(xing, hao):
    if not dengdai(xing, "login:", 480, "星%d" % hao):
        return False
    xing.sendline("root")
    dengdai(xing, "Password:", 20, "星%d" % hao)
    xing.sendline("openkylin")
    if not dengdai(xing, "#", 120, "星%d" % hao):
        return False
    time.sleep(1)
    xing.sendline("systemctl stop NetworkManager 2>/dev/null; ip link set enp0s2 up; "
                  "ip addr flush dev enp0s2; ip addr add %s/24 dev enp0s2" % IP_MAP[hao])
    dengdai(xing, "#", 40, "星%d" % hao)
    time.sleep(1)
    xing.sendline("mount -t 9p -o trans=virtio hostshare /mnt/share 2>&1")
    dengdai(xing, "#", 40, "星%d" % hao)
    xing.sendline("systemctl stop xintiao.service agent.service jiance.service 2>/dev/null; "
                  "systemctl disable xintiao.service agent.service jiance.service 2>/dev/null; "
                  "pkill -f xingxin_riscv64 2>/dev/null; pkill -f agent_yonghu 2>/dev/null; echo FU_WU_YI_QING")
    dengdai(xing, "FU_WU_YI_QING", 25, "星%d" % hao)
    time.sleep(1)
    return True


def miyao_du():
    try:
        with open(MIAO) as f:
            return json.load(f)
    except Exception:
        return None


def miyao_xie():
    jiu = miyao_du()
    if jiu and jiu.get("ling_pai"):
        return jiu
    xin = {"miyao": os.environ.get("WX_MIYAO") or secrets.token_hex(16),
           "ling_pai": os.environ.get("WX_LING_PAI") or secrets.token_hex(16)}
    with open(MIAO, "w") as f:
        json.dump(xin, f)
    return xin


def xin_rizhi(hao):
    try:
        with open(os.path.join(SHUJU, "xin%d.txt" % hao)) as f:
            return f.read()
    except Exception:
        return ""


def zuzhang_hao(hao):
    return "集群成员 3 个(存活 3)" in xin_rizhi(hao) or "成功加入集群" in xin_rizhi(hao)


def yaogce_zai(hao):
    return os.path.exists(os.path.join(SHUJU, "weixing%d.json" % hao))


def xin_qi_dong_ming(hao, miao, e_huan):
    env_qian = " ".join("%s=%s" % (k, v) for k, v in (e_huan or {}).items())
    if env_qian:
        env_qian += " "
    if hao == 1:
        return "%sWX_MIYAO=%s WX_LING_PAI=%s /mnt/share/xingxin_riscv64 weixing1 7946 192.168.50.1 > /mnt/share/shuju/xin1.txt 2>&1 &" % (env_qian, miao["miyao"], miao["ling_pai"])
    return "%sWX_MIYAO=%s WX_LING_PAI=%s /mnt/share/xingxin_riscv64 weixing%d 7946 192.168.50.%d 192.168.50.1:7946 > /mnt/share/shuju/xin%d.txt 2>&1 &" % (env_qian, miao["miyao"], miao["ling_pai"], hao, hao, hao)


def qidong_pingtai():
    miao = miyao_xie()
    for hao in (1, 2, 3):
        XINGS[hao] = qidong(hao)
    print("=== 三星并行启动 ===", flush=True)
    for hao in (1, 2, 3):
        if not denglu(XINGS[hao], hao):
            raise SystemExit("星%d 登录失败" % hao)
    print("=== 三星就绪 ===", flush=True)
    time.sleep(2)
    for hao in (1, 2, 3):
        XINGS[hao].sendline(
            "mkdir -p /mnt/share/shuju; /mnt/share/agent_yonghu weixing%d 3 /mnt/share/shuju "
            "> /mnt/share/shuju/weixing%d.json &" % (hao, hao))
        time.sleep(2)
    jie_shu = time.time() + 90
    while time.time() < jie_shu and not all(yaogce_zai(h) for h in (1, 2, 3)):
        time.sleep(2)
    print("=== 观测 agent 就绪(遥测落盘) ===", flush=True)
    for hao in (1, 2, 3):
        XINGS[hao].sendline(xin_qi_dong_ming(hao, miao, None))
        time.sleep(3)
    jie_shu = time.time() + 60
    while time.time() < jie_shu and not all(zuzhang_hao(h) for h in (1, 2, 3)):
        time.sleep(2)
    if not all(zuzhang_hao(h) for h in (1, 2, 3)):
        for hao in (1, 2, 3):
            print("xin%d: %s" % (hao, xin_rizhi(hao)[-200:]), flush=True)
        raise SystemExit("组网失败")
    print("=== 三星组网成功 ===", flush=True)


def cmd_run(ming):
    hao = int(ming["hao"])
    with SUO:
        x = XINGS[hao]
        x.sendline(ming["line"])
        tu = ming.get("expect")
        if tu:
            if not dengdai(x, tu, int(ming.get("timeout", 20)), "星%d" % hao):
                return {"ok": False, "cuo": "expect timeout: %s" % tu}
            return {"ok": True, "before": x.before[-2000:] if x.before else ""}
        return {"ok": True}


def cmd_rejoin(ming):
    hao = int(ming["hao"])
    miao = miyao_du()
    e_huan = ming.get("env") or {}
    jiu_daxiao = len(xin_rizhi(hao))
    with SUO:
        XINGS[hao].sendline("pkill -f xingxin_riscv64; sleep 1; echo XIN_QING_WAN")
        dengdai(XINGS[hao], "XIN_QING_WAN", 30, "星%d" % hao)
        XINGS[hao].sendline(xin_qi_dong_ming(hao, miao, e_huan))
    jie_shu = time.time() + 60
    while time.time() < jie_shu:
        zeng = xin_rizhi(hao)[jiu_daxiao:]
        if "成功加入集群" in zeng or "集群成员" in zeng:
            return {"ok": True}
        time.sleep(2)
    return {"ok": False, "cuo": "rejoin timeout"}


def cmd_chongzhi(ming):
    """重置:杀旧 xingxin 与 agent,重拉 agent(遥测)与 xingxin(按 env),等遥测+组网。"""
    hao = int(ming["hao"])
    miao = miyao_du()
    e_huan = ming.get("env") or {}
    with SUO:
        XINGS[hao].sendline("pkill -f xingxin_riscv64; pkill -f agent_yonghu; sleep 1; "
                            "rm -f /mnt/share/shuju/weixing%d.json; echo QING_WAN" % hao)
        dengdai(XINGS[hao], "QING_WAN", 30, "星%d" % hao)
        XINGS[hao].sendline("rm -f /mnt/share/shuju/weixing%d.json; "
                            "/mnt/share/agent_yonghu weixing%d 3 /mnt/share/shuju "
                            "> /mnt/share/shuju/weixing%d.json &" % (hao, hao, hao))
        time.sleep(2)
        XINGS[hao].sendline(xin_qi_dong_ming(hao, miao, e_huan))
    jie_shu = time.time() + 90
    while time.time() < jie_shu:
        if yaogce_zai(hao) and zuzhang_hao(hao):
            return {"ok": True}
        time.sleep(2)
    return {"ok": False, "cuo": "chongzhi timeout"}


def cmd_chongzhi_quan(ming):
    e_huan = ming.get("env") or {}
    jie = {}
    for hao in (1, 2, 3):
        jie[hao] = cmd_chongzhi({"hao": hao, "env": e_huan})
        if not jie[hao]["ok"]:
            break
    return {"ok": all(x["ok"] for x in jie.values()), "xiang": jie}


def cmd_rejoin_all(ming):
    jie = {}
    for hao in (1, 2, 3):
        jie[hao] = cmd_rejoin({"hao": hao, "env": ming.get("env")})
        if not jie[hao]["ok"]:
            break
        time.sleep(3)
    return {"ok": all(j["ok"] for j in jie.values()), "xiang": jie}


class KONG(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            shu = self.request.recv(4096).decode()
            ming = json.loads(shu.strip())
            leixing = ming.get("cmd")
            if leixing == "ping":
                hui = {"ok": True, "zu": [h for h in (1, 2, 3) if yaogce_zai(h)]}
            elif leixing == "run":
                hui = cmd_run(ming)
            elif leixing == "send":
                with SUO:
                    XINGS[int(ming["hao"])].sendline(ming["line"])
                hui = {"ok": True}
            elif leixing == "rejoin":
                hui = cmd_rejoin(ming)
            elif leixing == "rejoin_all":
                hui = cmd_rejoin_all(ming)
            elif leixing == "chongzhi":
                hui = cmd_chongzhi_quan(ming)
            elif leixing == "guanbi":
                hui = {"ok": True}
                self.request.sendall((json.dumps(hui) + "\n").encode())
                threading.Thread(target=guanbi, daemon=True).start()
                time.sleep(2)
                os._exit(0)
            else:
                hui = {"ok": False, "cuo": "unknown cmd"}
        except Exception as cuo:
            hui = {"ok": False, "cuo": str(cuo)}
        try:
            self.request.sendall((json.dumps(hui, ensure_ascii=False) + "\n").encode())
        except Exception:
            pass


def guanbi():
    for hao, x in XINGS.items():
        try:
            x.sendline("poweroff -f")
        except Exception:
            pass
    time.sleep(4)
    for x in XINGS.values():
        try:
            x.close()
        except Exception:
            pass
    subprocess.run(["pkill", "-f", "xing[123].qcow2"], capture_output=True)
    print("=== 三星已关闭 ===", flush=True)


def fuwu():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", KONG_ZHI_DUAN), KONG) as qi:
        print("=== 控制端口 %d 就绪,平台驻留中 ===" % KONG_ZHI_DUAN, flush=True)
        qi.serve_forever()


if __name__ == "__main__":
    if "--zhuangtai" in sys.argv:
        qemu = subprocess.run(["pgrep", "-fc", "xing[123].qcow2"], capture_output=True, text=True)
        print(json.dumps({"qemu": qemu.stdout.strip() or "0",
                          "yaoce": [h for h in (1, 2, 3) if yaogce_zai(h)]}, ensure_ascii=False))
        sys.exit(0)
    if "--guanbi" in sys.argv:
        guanbi()
        sys.exit(0)
    try:
        qidong_pingtai()
        fuwu()
    except KeyboardInterrupt:
        guanbi()
