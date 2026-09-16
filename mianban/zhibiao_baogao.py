#!/usr/bin/env python3
import glob
import json
import os
import re
import sys

import diaodu_yun as dd

DA_KAI = "<=60"


def du_ri(ri_lu):
    try:
        with open(ri_lu) as f:
            return f.read().splitlines()
    except Exception:
        return []


def du_jieguo_lie(shu_mulu):
    jieguo = []
    for lu in sorted(glob.glob(os.path.join(shu_mulu, "renwu_*.json"))):
        try:
            with open(lu) as f:
                hang = f.read().strip().splitlines()
        except Exception:
            continue
        for h in hang:
            try:
                g = json.loads(h)
            except Exception:
                continue
            if "renwu" in g:
                jieguo.append(g)
    return jieguo


def miao_shi(hhmmss):
    shi, fen, miao = hhmmss.split(":")
    return int(shi) * 3600 + int(fen) * 60 + int(miao)


def wei_shu(liebiao, bai):
    if not liebiao:
        return None
    pai = sorted(liebiao)
    return pai[min(len(pai) - 1, int(round((bai / 100.0) * (len(pai) - 1))))]


def ji_suan(ri_hang, jieguo_lie):
    pai_fa = {}
    for hang in ri_hang:
        m = re.match(r"^(\d\d:\d\d:\d\d)\|派发\|(rw-\d+)\|", hang)
        if m:
            pai_fa[m.group(2)] = m.group(1)
    quan_cheng = []
    for g in jieguo_lie:
        bh = g.get("renwu")
        if bh in pai_fa and g.get("wancheng"):
            cha = miao_shi(g["wancheng"]) - miao_shi(pai_fa[bh])
            if cha < 0:
                cha += 86400
            quan_cheng.append(cha)
    zhi_xing = [g.get("hao_shi_ms", 0) for g in jieguo_lie]
    zhi_da = sum(1 for g in jieguo_lie if g.get("laiyuan") != "JIEGUAN")
    jie_guan = sum(1 for g in jieguo_lie if g.get("laiyuan") == "JIEGUAN")
    qian_ru = []
    yun_qian = 0
    for hang in ri_hang:
        m = re.search(r"星间接管完成\|rw-\d+\|.*?云端观测全程([0-9.]+)秒", hang)
        if m:
            qian_ru.append(float(m.group(1)))
        if "云端迁移|" in hang:
            yun_qian += 1
    dai_fa = sum(1 for hang in ri_hang if "|入列|" in hang)
    xiao = sum(1 for hang in ri_hang if "|销账|" in hang)
    da_biao = sum(1 for t in qian_ru if t <= 60.0)
    return {
        "pai_fa_shu": len(pai_fa),
        "wan_cheng_shu": len(jieguo_lie),
        "zhi_da_shu": zhi_da,
        "jie_guan_shu": jie_guan,
        "yun_duan_qian_yi_shu": yun_qian,
        "ru_lie_dai_fa_shu": dai_fa,
        "xiao_zhang_shu": xiao,
        "quan_cheng_miao": {"p50": wei_shu(quan_cheng, 50), "p95": wei_shu(quan_cheng, 95),
                            "zui_da": wei_shu(quan_cheng, 100)},
        "zhi_xing_hao_miao": {"p50": wei_shu(zhi_xing, 50), "p95": wei_shu(zhi_xing, 95)},
        "jie_guan_hui_fu_miao": {"p50": wei_shu(qian_ru, 50), "p95": wei_shu(qian_ru, 95),
                                 "zui_da": wei_shu(qian_ru, 100) if qian_ru else None,
                                 "da_biao_60s_lv": round(100.0 * da_biao / len(qian_ru), 1) if qian_ru else None},
    }


def main():
    ri_lu = sys.argv[1] if len(sys.argv) > 1 else "/tmp/qemu_env/diaodu.log"
    bao = ji_suan(du_ri(ri_lu), du_jieguo_lie(dd.SHUJU))
    print("=" * 60)
    print("  星座任务调度指标报告  %s" % __import__("time").strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    print("派发任务: %d   完成: %d   (直达 %d / 星间接管 %d)" %
          (bao["pai_fa_shu"], bao["wan_cheng_shu"], bao["zhi_da_shu"], bao["jie_guan_shu"]))
    print("云端迁移: %d   入列待发: %d   销账: %d" %
          (bao["yun_duan_qian_yi_shu"], bao["ru_lie_dai_fa_shu"], bao["xiao_zhang_shu"]))
    qc = bao["quan_cheng_miao"]
    print("派发→完成 全程: p50=%.1fs p95=%.1fs 最大=%.1fs" % (qc["p50"], qc["p95"], qc["zui_da"]))
    zx = bao["zhi_xing_hao_miao"]
    print("星上执行耗时: p50=%dms p95=%dms" % (zx["p50"], zx["p95"]))
    hf = bao["jie_guan_hui_fu_miao"]
    if hf["p50"] is not None:
        print("接管恢复: p50=%.1fs p95=%.1fs 最大=%.1fs  60秒达标率=%s%%" %
              (hf["p50"], hf["p95"], hf["zui_da"], hf["da_biao_60s_lv"]))
    else:
        print("接管恢复: 本轮无接管事件")
    print("=" * 60)
    lu = os.path.join(dd.SHUJU, "zhibiao_baogao.json")
    try:
        with open(lu, "w") as f:
            json.dump(bao, f, ensure_ascii=False, indent=2)
        print("已写入 %s" % lu)
    except Exception:
        pass


if __name__ == "__main__":
    main()
