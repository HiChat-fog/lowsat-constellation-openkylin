#!/usr/bin/env python3
"""观测 agent 自身开销基准:同一固定负载,在 agent 开/关两种状态下各执行 n 轮,
比较任务执行耗时差异,并采集 agent 自身 RSS。
前置:三星平台驻留。输出: pinggu/chengguo/kaixiao_jieguo.json/.md

用法: python3 kaixiao_jizhun.py --lunshu 10 --canliang 2000000 --xing 1
"""
import argparse
import glob
import json
import os
import socket
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pingtai_kh import fa_ming, run  # noqa: E402

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHUJU = "/tmp/qemu_env/share/shuju"


def miyao_ling_pai():
    with open("/tmp/qemu_env/shiyan_miyao.json") as f:
        return json.load(f)["ling_pai"]


def pai_yi_ge(bianhao, canliang, hao):
    bao = {"mingling": "PAIFA", "ling_pai": miyao_ling_pai(),
           "renwu": {"bianhao": bianhao, "ming": "zai_gui_chu_li",
                     "canliang": canliang, "chang_shi": 1}}
    s = socket.create_connection(("127.0.0.1", 8010 + hao), timeout=5)
    s.sendall((json.dumps(bao) + "\n").encode())
    hui = json.loads(s.recv(128).decode())
    s.close()
    if "OK" not in hui.get("jieguo", ""):
        raise RuntimeError("PAIFA shibai: %s" % hui)


def deng_jie_guo(bianhao, chaoshi=120):
    jie_shu = time.time() + chaoshi
    while time.time() < jie_shu:
        for lu in glob.glob(os.path.join(SHUJU, "renwu_weixing*.json")):
            try:
                with open(lu) as f:
                    for hang in reversed(f.read().splitlines()):
                        if bianhao in hang:
                            g = json.loads(hang)
                            if g.get("jiedian") and "hao_shi_ms" in g:
                                return int(g["hao_shi_ms"])
            except Exception:
                pass
        time.sleep(0.3)
    raise TimeoutError(bianhao)


def ce_yi_lun(xu_hao, canliang, hao):
    bh = "rw-kx-%d-%d" % (xu_hao, int(time.time()))
    pai_yi_ge(bh, canliang, hao)
    return deng_jie_guo(bh)


def agent_zhuang_tai(hao, kai):
    """kai=True 确保在跑,否则杀掉;返回实际状态。"""
    if kai:
        hui = run(hao, "pidof agent_yonghu >/dev/null && echo AGENT_ON || "
                       "/mnt/share/agent_yonghu weixing%d 3 /mnt/share/shuju > "
                       "/mnt/share/shuju/weixing%d.json & echo AGENT_ON" % (hao, hao),
                  expect="AGENT_ON", timeout=30)
        time.sleep(3)
        return hui.get("ok", False)
    run(hao, "pkill -f agent_yonghu; echo AGENT_OFF", expect="AGENT_OFF", timeout=30)
    return True


def agent_rss_kb(hao):
    hui = run(hao, "grep VmRSS /proc/$(pidof agent_yonghu)/status; echo RSS_DONE",
              expect="RSS_DONE", timeout=30)
    if not hui.get("ok"):
        return None
    for hang in (hui.get("before") or "").splitlines():
        if "VmRSS" in hang:
            try:
                return int(hang.split()[1])
            except Exception:
                pass
    return None


def tong_ji(zhi):
    return {"n": len(zhi), "mean": round(statistics.mean(zhi), 1),
            "std": round(statistics.stdev(zhi), 1) if len(zhi) > 1 else 0.0,
            "min": min(zhi), "max": max(zhi)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lunshu", type=int, default=10)
    ap.add_argument("--canliang", type=int, default=2000000)
    ap.add_argument("--xing", type=int, default=1)
    can = ap.parse_args()
    if not fa_ming({"cmd": "ping"}).get("ok"):
        raise SystemExit("平台不在线:先 shiyan_pingtai.py --qidong")

    kai_shi = time.time()
    kai = [ce_yi_lun(i, can.canliang, can.xing) for i in range(can.lunshu)]
    rss = agent_rss_kb(can.xing)
    agent_zhuang_tai(can.xing, False)
    time.sleep(3)
    guan = [ce_yi_lun(1000 + i, can.canliang, can.xing) for i in range(can.lunshu)]
    agent_zhuang_tai(can.xing, True)
    time.sleep(5)

    cha = (statistics.mean(kai) - statistics.mean(guan)) / statistics.mean(guan) * 100.0
    bao = {"xing": can.xing, "canliang": can.canliang, "lunshu": can.lunshu,
           "agent_kai": tong_ji(kai), "agent_guan": tong_ji(guan),
           "kai_bi_guan_man": round(cha, 2),
           "agent_rss_kb": rss, "yong_shi_s": round(time.time() - kai_shi, 1)}
    cheng_guo_lu = os.path.join(GEN, "pinggu", "chengguo")
    os.makedirs(cheng_guo_lu, exist_ok=True)
    lu = os.path.join(cheng_guo_lu, "kaixiao_jieguo")
    with open(lu + ".json", "w") as f:
        json.dump(bao, f, ensure_ascii=False, indent=2)
    with open(lu + ".md", "w") as f:
        f.write("# agent 开销基准(星%d, 固定合成负载 canliang=%d, 各%d轮)\n\n"
                % (can.xing, can.canliang, can.lunshu))
        f.write("- agent 开: 执行耗时 mean±std %.1f±%.1f ms\n" % (bao["agent_kai"]["mean"], bao["agent_kai"]["std"]))
        f.write("- agent 关: 执行耗时 mean±std %.1f±%.1f ms\n" % (bao["agent_guan"]["mean"], bao["agent_guan"]["std"]))
        f.write("- 观测开销(开相对关): %.2f%%\n" % cha)
        f.write("- agent 自身 RSS: %s KB\n" % rss)
    print(json.dumps(bao, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
