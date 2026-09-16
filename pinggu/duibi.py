#!/usr/bin/env python3
import json
import math
import os
import random
import subprocess
import sys

JIAN_CE = os.environ.get("WX_JIAN_CE", "/tmp/jz")
BAO_GAO = os.environ.get("WX_DUIBI_BAOGAO", "/tmp/weixing_duibi_baogao.json")
DAO_MING = ["wendu", "dianya", "dianliu", "zitai", "jiaosudu"]
BAO_ZHI = 3.0
HUI_ZHI = 1.5
CHUANG = 30
ZONG_CHANG = 900

BIAO_JI = [
    {"dao": 0, "leixing": "TB", "kaishi": 360, "jieshu": 399},
    {"dao": 1, "leixing": "PIAO_YI", "kaishi": 480, "jieshu": 579},
    {"dao": 2, "leixing": "FANG_CHA", "kaishi": 660, "jieshu": 699},
    {"dao": 3, "leixing": "KA_SI", "kaishi": 760, "jieshu": 839},
]


def sheng_cheng_liu(zhong_zi):
    sui = random.Random(zhong_zi)
    liu = []
    for t in range(ZONG_CHANG):
        zhi = [20.0 + 3.0 * math.sin(t * 0.02) + sui.gauss(0, 0.4),
               28.0 + 0.5 * math.sin(t * 0.01) + sui.gauss(0, 0.15),
               2.4 + 0.3 * math.sin(t * 0.03) + sui.gauss(0, 0.06),
               15.0 * math.sin(t * 0.05) + sui.gauss(0, 0.8),
               3.0 * math.sin(t * 0.02 + 1.0) + sui.gauss(0, 0.2)]
        if 360 <= t < 400:
            zhi[0] += 10.0
        if 480 <= t < 580:
            zhi[1] += min((t - 480) * 0.2, 8.0)
        if 660 <= t < 700:
            zhi[2] = 2.4 + 1.8 * math.sin(t * 0.5) + sui.gauss(0, 0.1)
        if 760 <= t < 840:
            zhi[3] = 15.0 * math.sin(760 * 0.05)
        liu.append(zhi)
    return liu


def ji_xian_jian_ce(liu):
    shijian = []
    chuangkou = [[0.0] * CHUANG for _ in range(5)]
    kuan = 0
    guai = [0] * 5
    for t, zhi in enumerate(liu):
        for j in range(5):
            if kuan < CHUANG:
                chuangkou[j][kuan] = zhi[j]
                continue
            jun = sum(chuangkou[j]) / CHUANG
            fang = math.sqrt(sum((v - jun) ** 2 for v in chuangkou[j]) / CHUANG)
            if fang < 1e-9:
                fang = 1e-9
            z = (zhi[j] - jun) / fang
            if z > BAO_ZHI and not guai[j]:
                guai[j] = 1
                shijian.append({"t": t, "dao": j, "leixing": "Z", "dongzuo": "ALARM"})
            elif z < HUI_ZHI and guai[j]:
                guai[j] = 0
                shijian.append({"t": t, "dao": j, "leixing": "Z", "dongzuo": "RECOVER"})
            chuangkou[j].pop(0)
            chuangkou[j].append(zhi[j])
        if kuan < CHUANG:
            kuan += 1
    return shijian


def you_hua_jian_ce(liu):
    if not os.path.exists(JIAN_CE):
        sys.exit("que shao %s, xian yun xing: make ceshi-c" % JIAN_CE)
    shu_ru = "\n".join(" ".join("%.6f" % v for v in zhi) for zhi in liu) + "\n"
    p = subprocess.run([JIAN_CE, "--shuru"], input=shu_ru, capture_output=True,
                       text=True, timeout=120)
    shijian = []
    for hang in p.stdout.splitlines():
        ge = hang.split("|")
        if len(ge) < 5 or ge[0] not in ("ALARM", "RECOVER", "GENG_LEI"):
            continue
        dongzuo = "GENG_LEI" if ge[0] == "GENG_LEI" else ge[0]
        dao_bian = int(ge[3][3:]) if ge[3].startswith("dao") else DAO_MING.index(ge[3])
        shijian.append({"t": int(ge[2].split("=")[1]), "dao": dao_bian,
                        "leixing": ge[4].split("=")[1], "dongzuo": dongzuo})
    return shijian


def zhi_biao(shijian, you_leixing):
    bao = [s for s in shijian if s["dongzuo"] == "ALARM"]
    hui = [s for s in shijian if s["dongzuo"] == "RECOVER"]
    ge_lei = {}
    zhao_dao_shu = 0
    yan_chi_lie = []
    for m in BIAO_JI:
        neis = [s for s in bao if s["dao"] == m["dao"] and m["kaishi"] - 2 <= s["t"] <= m["jieshu"]]
        jian_chu = bool(neis)
        zhao_dao_shu += 1 if jian_chu else 0
        yan_chi = neis[0]["t"] - m["kaishi"] if neis else None
        if yan_chi is not None:
            yan_chi_lie.append(yan_chi)
        lei_zheng = None
        if you_leixing and jian_chu:
            lei_zheng = any(s["leixing"] == m["leixing"] for s in
                            [x for x in shijian if x["dongzuo"] in ("ALARM", "GENG_LEI")
                             and x["dao"] == m["dao"]
                             and m["kaishi"] - 2 <= x["t"] <= m["jieshu"] + 60])
        ge_lei["%d_%s" % (m["dao"], m["leixing"])] = {
            "jian_chu": jian_chu, "yan_chi": yan_chi, "lei_zheng": lei_zheng}
    wu_bao = [s for s in bao
              if not any(s["dao"] == m["dao"] and m["kaishi"] - 2 <= s["t"] <= m["jieshu"] + 5
                         for m in BIAO_JI)]
    guo_zao = [s for s in hui
               if any(s["dao"] == m["dao"] and m["kaishi"] <= s["t"] <= m["jieshu"]
                      for m in BIAO_JI)]
    return {"jian_chu_lv": round(100.0 * zhao_dao_shu / len(BIAO_JI), 1),
            "wu_bao": len(wu_bao), "guo_zao_hui_fu": len(guo_zao),
            "ping_jun_yan_chi": round(sum(yan_chi_lie) / len(yan_chi_lie), 1) if yan_chi_lie else None,
            "ge_lei": ge_lei}


def main():
    zhong_zi = 20260912
    liu = sheng_cheng_liu(zhong_zi)
    ji_xian = zhi_biao(ji_xian_jian_ce(liu), False)
    you_hua = zhi_biao(you_hua_jian_ce(liu), True)
    bao = {"zhong_zi": zhong_zi, "ji_xian": ji_xian, "you_hua": you_hua}
    print("=" * 72)
    print("  异常检测对比评估  基线=固定窗口z分数  优化=稳健z+斜率+方差比+卡死  种子=%d" % zhong_zi)
    print("=" * 72)
    for ming, zhi in (("基线(固定z分数)", ji_xian), ("优化(自适应四机制)", you_hua)):
        print("-- %s --" % ming)
        for jian, m in (("TB", 0), ("PIAO_YI", 1), ("FANG_CHA", 2), ("KA_SI", 3)):
            g = zhi["ge_lei"]["%d_%s" % (m, jian)]
            lei = "-" if g["lei_zheng"] is None else ("zheng" if g["lei_zheng"] else "wu")
            print("  %s: 检出=%s 延迟=%s 类型=%s" %
                  (jian.ljust(8), "shi" if g["jian_chu"] else "fou",
                   ("%d拍" % g["yan_chi"]) if g["yan_chi"] is not None else "-", lei))
        print("  检出率=%.0f%%  误报=%d次  过早恢复=%d次  平均延迟=%s拍" %
              (zhi["jian_chu_lv"], zhi["wu_bao"], zhi["guo_zao_hui_fu"],
               zhi["ping_jun_yan_chi"] if zhi["ping_jun_yan_chi"] is not None else "-"))
    print("=" * 72)
    with open(BAO_GAO, "w") as f:
        json.dump(bao, f, ensure_ascii=False, indent=2)
    print("已写入 %s" % BAO_GAO)
    if you_hua["jian_chu_lv"] < ji_xian["jian_chu_lv"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
