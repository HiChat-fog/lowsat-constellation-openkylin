#!/usr/bin/env python3
import os

import numpy as np
from scipy.io import loadmat

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHU_JU = (os.environ.get("WX_DIANCHI_DIR")
          or os.environ.get("WX_DIANCHI_SHUJU")
          or os.path.join(os.path.dirname(GEN), "shiyan", "shuju_dianchi"))
BAO_GAO = "/tmp/weixing_dianchi_baogao.json"
SOH_XIAN = 0.70
JIAN_CHA = [40, 60, 80, 100, 120]
CHUANG = 20


def du_rong_liang(lu):
    d = loadmat(lu)
    ks = [k for k in d if not k.startswith("__")][0]
    top = d[ks][0, 0][0]
    leixing = [str(x[0]).strip() for x in top["type"][0]]
    shu = top["data"][0]
    rong = []
    for i in range(len(leixing)):
        if leixing[i] != "discharge":
            continue
        dd = shu[i][0, 0]
        if "Capacity" in (dd.dtype.names or ()):
            zhi = float(dd["Capacity"][0][0])
            if zhi > 0.1:
                rong.append(zhi)
    return np.array(rong)


def rul_yu_ce(rong, t, xian):
    soh = rong / rong[0]
    kai = max(0, t - CHUANG)
    chuang = soh[kai:t + 1]
    x = np.arange(len(chuang), dtype=float)
    xie, jie = np.polyfit(x, chuang, 1)
    if xie >= -1e-9:
        return -1.0
    cha = chuang[-1] - SOH_XIAN
    if cha <= 0:
        return 0.0
    return cha / (-xie)


def main():
    bao = {"shu_ju": SHU_JU, "lai_yuan": "NASA PCoE Prognostics Data Repository, 18650 Li-ion 2Ohm 恒流放电老化数据", "dian_chi": {}}
    huai = 0
    for ming in ("B0005", "B0006"):
        lu = os.path.join(SHU_JU, ming + ".mat")
        if not os.path.exists(lu):
            print("[skip] %s bu cun zai" % ming)
            continue
        rong = du_rong_liang(lu)
        soh = rong / rong[0]
        yue = np.where(soh < SOH_XIAN)[0]
        shi_ji = int(yue[0]) if len(yue) else -1
        jian = {}
        cuo_lie = []
        for t in JIAN_CHA:
            if t >= len(soh) - 2:
                continue
            yu = rul_yu_ce(rong, t, SOH_XIAN)
            shi = max(shi_ji - t, 0) if shi_ji >= 0 else -1
            wu = abs(yu - shi) / max(shi, 1) if (yu >= 0 and shi >= 0) else None
            jian[t] = {"yu_ce": round(float(yu), 1), "shi_ji": shi,
                       "wu_cha": round(float(wu), 3) if wu is not None else None}
            if wu is not None:
                cuo_lie.append(wu)
        jun_wu = round(float(np.mean(cuo_lie)), 3) if cuo_lie else None
        bao["dian_chi"][ming] = {"xun_huan_shu": len(soh),
                                 "soh_shou": round(float(soh[0]), 3),
                                 "soh_wei": round(float(soh[-1]), 3),
                                 "shi_ji_70": shi_ji, "jian_cha": jian,
                                 "jun_xiang_dui_wu_cha": jun_wu}
        ok = jun_wu is not None and jun_wu <= 0.30
        print("=" * 64)
        print("  %s: %d 个放电循环  SOH %.0f%% -> %.0f%%  70%%阈值在第 %d 圈" %
              (ming, len(soh), soh[0] * 100, soh[-1] * 100, shi_ji))
        for t, z in jian.items():
            print("  第 %3d 圈预测剩余 %6.1f 圈, 实际 %4d 圈, 相对误差 %s" %
                  (t, z["yu_ce"], z["shi_ji"],
                   ("%.0f%%" % (z["wu_cha"] * 100)) if z["wu_cha"] is not None else "-"))
        print("  平均相对误差: %s  (门槛 30%%, 判定 %s)" %
              (("%.0f%%" % (jun_wu * 100)) if jun_wu is not None else "-",
               "PASS" if ok else "FAIL"))
        if not ok:
            huai = 1
    print("=" * 64)
    with open(BAO_GAO, "w") as f:
        import json
        json.dump(bao, f, ensure_ascii=False, indent=2)
    if huai:
        print("DIAN_CHI_YAN_ZHENG FAIL")
        return 1
    print("DIAN_CHI_YAN_ZHENG PASS: xian xing wai tui RUL fang fa zai zhen shi lao hua shu ju shang da biao")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
