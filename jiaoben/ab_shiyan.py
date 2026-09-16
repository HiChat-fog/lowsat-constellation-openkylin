#!/usr/bin/env python3
"""真机 SJF vs FCFS 调度 A/B 实验。前置:三星平台已驻留(shiyan_pingtai.py --qidong)。

原理:以突发模式向云端调度器一次性注入 K 个混合 canliang 任务,派发速率高于
三星执行能力,云端形成待发队列;SJF 按 canliang 升序出队,FCFS 按创建序出队。
每个任务的实际执行耗时与 canliang 成正比(sha256 合成任务),故 canliang 是
准确的执行量预估,SJF 的排序信息是真实有效的。

用法:
    python3 ab_shiyan.py --lunshu 10 --renwushu 40 --bei 20
输出:
    pinggu/chengguo/ab_diaodu_jieguo.json + ab_diaodu_jieguo.md
"""
import argparse
import glob
import json
import os
import re
import statistics
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pingtai_kh import fa_ming  # noqa: E402

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHUJU = "/tmp/qemu_env/share/shuju"
YUN = "/tmp/qemu_env"
WAN_CHENG = re.compile(r"完成\|rw-(\d+)\|([^|]+)\|执行(\d+)ms\|全程([0-9.]+)秒")


def miyao_ling_pai():
    with open(os.path.join(YUN, "shiyan_miyao.json")) as f:
        return json.load(f)["ling_pai"]


def qing_li():
    for lu in glob.glob(os.path.join(SHUJU, "renwu_*.json")):
        os.remove(lu)
    for ming in ("diaodu_taizhang.json",):
        lu = os.path.join(SHUJU, ming)
        if os.path.exists(lu):
            os.remove(lu)


def yun_lun(celue, renwushu, bei, chaoshi, hao, bingfa=2):
    # 每轮重置三星:杀旧 xingxin/agent 后重拉,清空在途任务与完成缓存并按 CPU 数设并发,
    # 避免上一轮残留与 CPU 超订(并发>核数会把单任务拖过重派阈值,引发重复执行)。
    chong = fa_ming({"cmd": "chongzhi", "env": {"WX_RENWU_BINGFA": str(bingfa)}}, chaoshi=300)
    if not chong.get("ok"):
        return {"celue": celue, "run": hao, "renwushu": renwushu, "bei": bei,
                "yong_shi_s": 0, "wan_cheng_shu": 0, "renwu": {}, "cuo": "chongzhi shibai"}
    time.sleep(3)
    qing_li()
    log_lu = os.path.join(YUN, "ab_%s_run%d.log" % (celue.lower(), hao))
    logf = open(log_lu, "w", buffering=1)
    env = dict(os.environ, WX_CELUE=celue, WX_BAOFASHU=str(renwushu),
               WX_BAOFASHU_BEI=str(bei), WX_PAIFA_LUN_QI="1", WX_PAIFA_MEI_LUN="6",
               WX_CHAOSHI=str(max(chaoshi, 120)), WX_LING_PAI=miyao_ling_pai())
    qishi = time.time()
    guo = subprocess.Popen([sys.executable, os.path.join(GEN, "mianban", "diaodu_yun.py")],
                           stdout=logf, stderr=subprocess.STDOUT, env=env)
    wan = {}
    try:
        while time.time() - qishi < chaoshi:
            try:
                with open(log_lu) as f:
                    for h in f.read().splitlines():
                        m = WAN_CHENG.search(h)
                        if m:
                            wan[m.group(1)] = {"jiedian": m.group(2),
                                               "hao_shi_ms": int(m.group(3)),
                                               "quan_cheng_s": float(m.group(4))}
            except FileNotFoundError:
                pass
            if len(wan) >= renwushu:
                break
            time.sleep(2)
    finally:
        guo.terminate()
        logf.close()
    can_liang = {str(i): (200000 + ((i * 37) % 4) * 100000) * bei for i in range(1, renwushu + 1)}
    for bh in wan:
        wan[bh]["canliang"] = can_liang.get(bh)
    return {"celue": celue, "run": hao, "renwushu": renwushu, "bei": bei,
            "yong_shi_s": round(time.time() - qishi, 1), "wan_cheng_shu": len(wan),
            "renwu": wan}


def tong_ji(zhi):
    zhi = sorted(zhi)
    if not zhi:
        return {"n": 0}
    n = len(zhi)
    p50 = zhi[n // 2] if n % 2 else (zhi[n // 2 - 1] + zhi[n // 2]) / 2
    p95 = zhi[min(n - 1, int(n * 0.95))]
    return {"n": n, "mean": round(statistics.mean(zhi), 2),
            "std": round(statistics.stdev(zhi), 2) if n > 1 else 0.0,
            "p50": round(p50, 2), "p95": round(p95, 2)}


def hui_zong(jie_guo_lie, bei):
    bao = {"bei": bei, "celue": {}}
    for celue in ("SJF", "FCFS"):
        lun = [j for j in jie_guo_lie if j["celue"] == celue]
        if not lun:
            continue
        duan = [t for j in lun for t in j["renwu"].values() if t["canliang"] and t["canliang"] <= 300000 * bei]
        chang = [t for j in lun for t in j["renwu"].values() if t["canliang"] and t["canliang"] > 300000 * bei]
        bao["celue"][celue] = {
            "runs": len(lun),
            "wan_cheng_lv": round(sum(j["wan_cheng_shu"] for j in lun) / (len(lun) * lun[0]["renwushu"]), 3),
            "quan_cheng": tong_ji([t["quan_cheng_s"] for j in lun for t in j["renwu"].values()]),
            "duan_renwu": tong_ji([t["quan_cheng_s"] for t in duan]),
            "chang_renwu": tong_ji([t["quan_cheng_s"] for t in chang]),
            "zhi_xing": tong_ji([t["hao_shi_ms"] for j in lun for t in j["renwu"].values()]),
        }
    return bao


def xie_baogao(bao, lu):
    with open(lu + ".json", "w") as f:
        json.dump(bao, f, ensure_ascii=False, indent=2)
    hang = ["# 真机调度 A/B:SJF vs FCFS(三星 QEMU,突发负载 %d 任务,cangliang 倍率 %d)"
            % (bao.get("renwushu", 0), bao["bei"]), ""]
    for celue, x in bao["celue"].items():
        hang.append("## %s(%d 轮)" % (celue, x["runs"]))
        hang.append("- 全程 mean±std: %.2f±%.2f 秒, p50 %.2f, p95 %.2f" %
                    (x["quan_cheng"]["mean"], x["quan_cheng"]["std"],
                     x["quan_cheng"]["p50"], x["quan_cheng"]["p95"]))
        hang.append("- 短任务(≤300k×%d) 全程: %s" % (bao["bei"], x["duan_renwu"]))
        hang.append("- 长任务 全程: %s" % x["chang_renwu"])
        hang.append("- 完成率: %s" % x["wan_cheng_lv"])
        hang.append("")
    with open(lu + ".md", "w") as f:
        f.write("\n".join(hang) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lunshu", type=int, default=10)
    ap.add_argument("--renwushu", type=int, default=40)
    ap.add_argument("--bei", type=int, default=8)
    ap.add_argument("--bingfa", type=int, default=2)
    ap.add_argument("--chaoshi", type=int, default=900)
    can = ap.parse_args()

    cheng_guo_lu = os.path.join(GEN, "pinggu", "chengguo")
    os.makedirs(cheng_guo_lu, exist_ok=True)
    if not fa_ming({"cmd": "ping"}).get("ok"):
        raise SystemExit("平台不在线:先 shiyan_pingtai.py --qidong")
    jie_guo_lie = []
    for celue in ("SJF", "FCFS"):
        for hao in range(1, can.lunshu + 1):
            print("=== %s 第%d/%d轮 ===" % (celue, hao, can.lunshu), flush=True)
            jie = yun_lun(celue, can.renwushu, can.bei, can.chaoshi, hao, can.bingfa)
            print("    完成 %d/%d,用时 %.0fs" % (jie["wan_cheng_shu"], can.renwushu, jie["yong_shi_s"]), flush=True)
            jie_guo_lie.append(jie)
            with open(os.path.join(cheng_guo_lu, "ab_%s_run%d.json" % (celue.lower(), hao)), "w") as f:
                json.dump(jie, f, ensure_ascii=False, indent=2)
    bao = hui_zong(jie_guo_lie, can.bei)
    bao["renwushu"] = can.renwushu
    xie_baogao(bao, os.path.join(cheng_guo_lu, "ab_diaodu_jieguo"))
    print(json.dumps(bao, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
