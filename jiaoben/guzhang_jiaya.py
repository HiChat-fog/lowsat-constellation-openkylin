#!/usr/bin/env python3
"""故障注入加压实验:测量 memberlist 故障感知与接管时间,以及丢包/断链下的退化。
前置:三星平台驻留(shiyan_pingtai.py --qidong)。需要 sudo 执行 tc/iplink(密码经
环境变量 WX_SU_PW 传入,不入库)。

模式(--moshi):
  kill9    kill -9 星2 xingxin,先派一个长任务到星2,测 感知/接管/任务迁移 时间
  fenqu    ip link set xingtap2 down 模拟链路分区,测感知时间,之后恢复
  diubao   netem 丢包扫描(默认 0/2/5/10/20%),每档 kill9 测感知时间;
           --tiao_you 时以调优 memberlist 参数(快 suspicion,高重传)重启集群对比

用法:
    python3 guzhang_jiaya.py --moshi kill9 --lunshu 10
    python3 guzhang_jiaya.py --moshi diubao --sunhao 0,2,5,10,20 --lunshu 5 [--tiao_you]
输出: pinggu/chengguo/guzhang_<moshi>_jieguo.json/.md
"""
import argparse
import glob
import json
import os
import re
import socket
import statistics
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pingtai_kh import fa_ming, run, xin_ri_zhui_jia, ri_daxiao  # noqa: E402

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHUJU = "/tmp/qemu_env/share/shuju"
YUN = "/tmp/qemu_env"
LI_KAI = re.compile(r"节点离开: weixing2")
JIE_GUAN = re.compile(r"接管")


def sudo_tc(ming):
    mima = os.environ.get("WX_SU_PW", "")
    subprocess.run(["sudo", "-S", "-p", ""] + ming, input=(mima + "\n").encode(),
                   capture_output=True, timeout=30, check=True)


def miyao_ling_pai():
    with open(os.path.join(YUN, "shiyan_miyao.json")) as f:
        return json.load(f)["ling_pai"]


def pai_chang_renwu(hao=2, bianhao="rw-kill9"):
    bao = {"mingling": "PAIFA", "ling_pai": miyao_ling_pai(),
           "renwu": {"bianhao": "%s-%d" % (bianhao, int(time.time())),
                     "ming": "zai_gui_chu_li", "canliang": 3000000, "chang_shi": 1}}
    s = socket.create_connection(("127.0.0.1", 8010 + hao), timeout=5)
    s.sendall((json.dumps(bao) + "\n").encode())
    hui = json.loads(s.recv(128).decode())
    s.close()
    return hui


def jieguo_zhao(bianhao_qian, kai_shi, chaoshi=90):
    """轮询结果文件,返回 (laiyuan=JIEGUAN 的相对秒) 或 None。"""
    jie_shu = time.time() + chaoshi
    while time.time() < jie_shu:
        for lu in glob.glob(os.path.join(SHUJU, "renwu_weixing*.json")):
            try:
                with open(lu) as f:
                    for hang in f.read().splitlines():
                        if "renwu" in hang and bianhao_qian in hang:
                            g = json.loads(hang)
                            if g.get("laiyuan") == "JIEGUAN":
                                return round(time.time() - kai_shi, 1)
            except Exception:
                pass
        time.sleep(0.5)
    return None


def gan_zhi_shi_jian(kai_shi, chaoshi=120):
    """自 kai_shi(host 时间戳)起,轮询星1/星3 心跳日志新增内容中的 节点离开/接管 标记。"""
    daxiao = {h: ri_daxiao(h) for h in (1, 3)}
    t_li_kai = t_jie_guan = None
    jie_shu = time.time() + chaoshi
    while time.time() < jie_shu and (t_li_kai is None or t_jie_guan is None):
        for h in (1, 3):
            zeng = xin_ri_zhui_jia(h, daxiao[h])
            if t_li_kai is None and LI_KAI.search(zeng):
                t_li_kai = round(time.time() - kai_shi, 1)
            if t_jie_guan is None and JIE_GUAN.search(zeng):
                t_jie_guan = round(time.time() - kai_shi, 1)
        time.sleep(0.3)
    return t_li_kai, t_jie_guan


def qing_renwu_wen():
    for lu in glob.glob(os.path.join(SHUJU, "renwu_*.json")):
        os.remove(lu)


def lun_kill9(i, yao_renwu=True):
    qing_renwu_wen()
    if yao_renwu:
        hui = pai_chang_renwu()
        if "OK" not in hui.get("jieguo", ""):
            return {"run": i, "cuo": "chang renwu PAIFA failed: %s" % hui}
        time.sleep(2)
    kai_shi = time.time()
    run(2, "pkill -9 -x xingxin_riscv64; echo KILL9_DONE", expect="KILL9_DONE", timeout=30)
    t_li_kai, t_jie_guan = gan_zhi_shi_jian(kai_shi)
    qian_yi = jieguo_zhao("rw-kill9", kai_shi, chaoshi=90) if yao_renwu else None
    hui = fa_ming({"cmd": "rejoin", "hao": 2})
    time.sleep(8)
    return {"run": i, "li_kai_s": t_li_kai, "jie_guan_s": t_jie_guan,
            "qian_yi_s": qian_yi, "rejoin": hui.get("ok", False)}


def lun_fenqu(i):
    kai_shi = time.time()
    sudo_tc(["ip", "link", "set", "xingtap2", "down"])
    t_li_kai, _ = gan_zhi_shi_jian(kai_shi)
    sudo_tc(["ip", "link", "set", "xingtap2", "up"])
    time.sleep(15)
    hui = fa_ming({"cmd": "ping", })
    return {"run": i, "li_kai_s": t_li_kai, "ping": hui.get("ok", False)}


def lun_diubao(i, sun_hao):
    sudo_tc(["tc", "qdisc", "replace", "dev", "xingtap2", "root", "netem", "loss", "%d%%" % sun_hao])
    time.sleep(10)
    try:
        jie = lun_kill9(i, yao_renwu=False)
    finally:
        sudo_tc(["tc", "qdisc", "del", "dev", "xingtap2", "root"])
        time.sleep(5)
    return jie


def chong_qi_ji_qun(e_huan=None):
    """rejoin_all 以统一参数重启三星星间进程(清空旧日志标记)。"""
    return fa_ming({"cmd": "rejoin_all", "env": e_huan or {}})


def tong_ji(zhi):
    zhi = [z for z in zhi if z is not None]
    if not zhi:
        return {"n": 0, "mean": None, "std": None, "max": None}
    return {"n": len(zhi), "mean": round(statistics.mean(zhi), 2),
            "std": round(statistics.stdev(zhi), 2) if len(zhi) > 1 else 0.0,
            "max": max(zhi), "min": min(zhi)}


def xie_baogao(bao, lu):
    with open(lu + ".json", "w") as f:
        json.dump(bao, f, ensure_ascii=False, indent=2)
    hang = ["# 故障注入实测(%s)" % bao.get("moshi", ""), ""]
    for ming, x in bao.get("hui_zong", {}).items():
        hang.append("- %s: %s" % (ming, json.dumps(x, ensure_ascii=False)))
    hang.append("")
    for j in bao.get("xiang_jie", [])[:20]:
        hang.append("  " + json.dumps(j, ensure_ascii=False))
    with open(lu + ".md", "w") as f:
        f.write("\n".join(hang) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--moshi", required=True, choices=["kill9", "fenqu", "diubao"])
    ap.add_argument("--lunshu", type=int, default=10)
    ap.add_argument("--sunhao", default="0,2,5,10,20")
    ap.add_argument("--tiao_you", action="store_true")
    can = ap.parse_args()

    cheng_guo_lu = os.path.join(GEN, "pinggu", "chengguo")
    os.makedirs(cheng_guo_lu, exist_ok=True)
    if not fa_ming({"cmd": "ping"}).get("ok"):
        raise SystemExit("平台不在线:先 shiyan_pingtai.py --qidong")

    xiang = []
    hui = {}
    tiao_huan = {"WX_SUSPICION_MULT": "3", "WX_RETRANSMIT_MULT": "8"} if can.tiao_you else None
    if can.tiao_you:
        print("=== 以调优参数重启集群 ===", flush=True)
        chong_qi_ji_qun(tiao_huan)
        time.sleep(5)
    try:
        if can.moshi == "kill9":
            for i in range(1, can.lunshu + 1):
                print("kill9 第%d/%d轮" % (i, can.lunshu), flush=True)
                xiang.append(lun_kill9(i))
                time.sleep(5)
            hui = {"li_kai": tong_ji([x["li_kai_s"] for x in xiang]),
                   "jie_guan": tong_ji([x["jie_guan_s"] for x in xiang]),
                   "qian_yi": tong_ji([x.get("qian_yi_s") for x in xiang])}
        elif can.moshi == "fenqu":
            for i in range(1, can.lunshu + 1):
                print("fenqu 第%d/%d轮" % (i, can.lunshu), flush=True)
                xiang.append(lun_fenqu(i))
                time.sleep(5)
            hui = {"li_kai": tong_ji([x["li_kai_s"] for x in xiang])}
        elif can.moshi == "diubao":
            for sun in [int(s) for s in can.sunhao.split(",")]:
                dang = []
                for i in range(1, can.lunshu + 1):
                    print("diubao %d%% 第%d/%d轮" % (sun, i, can.lunshu), flush=True)
                    jie = lun_diubao(i, sun)
                    jie["sun_hao"] = sun
                    dang.append(jie)
                    xiang.append(jie)
                    time.sleep(5)
                hui["loss_%d%%" % sun] = tong_ji([x["li_kai_s"] for x in dang])
    finally:
        if can.tiao_you:
            print("=== 恢复默认参数重启集群 ===", flush=True)
            chong_qi_ji_qun(None)
            time.sleep(5)

    bao = {"moshi": can.moshi + ("(tuned)" if can.tiao_you else ""),
           "lunshu": can.lunshu, "hui_zong": hui, "xiang_jie": xiang}
    hou_zhui = "_tiao_you" if can.tiao_you else ""
    xie_baogao(bao, os.path.join(cheng_guo_lu, "guzhang_%s%s_jieguo" % (can.moshi, hou_zhui)))
    print(json.dumps(hui, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
