#!/usr/bin/env python3
import csv
import json
import math
import os
import subprocess
import sys

import warnings

import numpy as np

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../waibu/..")
sys.path.insert(0, GEN)
from waibu.tsb_ad.evaluation.metrics import get_metrics as tsb_get_metrics

JIAN_CE = os.environ.get("WX_JIAN_CE", "/tmp/jz")
SHU_JU = (os.environ.get("WX_SMAP_DIR")
          or os.environ.get("WX_SMAP_SHUJU")
          or os.path.join(os.path.dirname(GEN), "shiyan", "shuju_smap"))
BAO_GAO = os.environ.get("WX_SMAP_BAOGAO", "/tmp/weixing_smap_baogao.json")
TONG_DAO = ["T-1", "P-1", "C-1", "E-1"]
CHUANG = 30
CAN_KAO_CHANG = 300
TSB_CHUANG = 100

CAN_ZHAO = {
    "lai_yuan": "Hundman et al., Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic Thresholding, KDD 2018 (NASA JPL Telemanom)",
    "fang_fa": "LSTM 预测 + 非参数动态阈值(离线, GPU)",
    "hui_zong": {"SMAP": 0.94, "MSL": 0.91},
    "shuo_ming": "论文汇总口径的 F1, 用作参照系; 本评估为轻量在线方法在单通道子集上的结果, 二者量纲不同不可直接排名"
}


def du_biao_qian(chan_id):
    with open(os.path.join(SHU_JU, "labeled_anomalies.csv")) as f:
        for hang in csv.DictReader(f):
            if hang["chan_id"] == chan_id:
                return [tuple(x) for x in json.loads(hang["anomaly_sequences"])]
    return []


def jia_zai(chan_id):
    a = np.load(os.path.join(SHU_JU, chan_id + ".npy"))
    return a


def ni_huo_yue(shijian, zong_chang, dao):
    huo = [False] * zong_chang
    kai = None
    for s in sorted(shijian, key=lambda x: x["t"]):
        if s["dao"] != dao:
            continue
        if s["dongzuo"] == "ALARM" and kai is None:
            kai = s["t"]
        elif s["dongzuo"] == "RECOVER" and kai is not None:
            for i in range(kai, min(s["t"], zong_chang)):
                huo[i] = True
            kai = None
    if kai is not None:
        for i in range(kai, zong_chang):
            huo[i] = True
    return huo


def ni_huo_yue_zong(shijian, zong_chang, dao_shu):
    huo = [False] * zong_chang
    for j in range(dao_shu):
        ge_dao = ni_huo_yue(shijian, zong_chang, j)
        huo = [a or b for a, b in zip(huo, ge_dao)]
    return huo


def dian_zhen_shu(huo):
    return np.asarray([1.0 if x else 0.0 for x in huo])


def dian_biao_shu(biao_qian, zong_chang):
    biao = np.zeros(zong_chang, dtype=int)
    for qi, zhi in biao_qian:
        biao[qi:min(zhi + 1, zong_chang)] = 1
    return biao


def vus_pr_zong(shijian, zong_chang, dao_shu, biao_qian):
    huo = ni_huo_yue_zong(shijian, zong_chang, dao_shu)
    return tsb_get_metrics(dian_zhen_shu(huo), dian_biao_shu(biao_qian, zong_chang),
                           slidingWindow=TSB_CHUANG)["VUS-PR"]


def dian_tiao_zheng(huo, biao_qian):
    zong_chang = len(huo)
    tiao = list(huo)
    for qi, zhi in biao_qian:
        if any(huo[i] for i in range(qi, min(zhi + 1, zong_chang))):
            for i in range(qi, min(zhi + 1, zong_chang)):
                tiao[i] = True
    biao = [False] * zong_chang
    for qi, zhi in biao_qian:
        for i in range(qi, min(zhi + 1, zong_chang)):
            biao[i] = True
    tp = sum(1 for i in range(zong_chang) if tiao[i] and biao[i])
    fp = sum(1 for i in range(zong_chang) if tiao[i] and not biao[i])
    fn = sum(1 for i in range(zong_chang) if not tiao[i] and biao[i])
    jing = tp / (tp + fp) if tp + fp else 0.0
    zhao = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * jing * zhao / (jing + zhao) if jing + zhao else 0.0
    duan_zhao = sum(1 for qi, zhi in biao_qian
                    if any(huo[i] for i in range(qi, min(zhi + 1, zong_chang))))
    return {"tp": tp, "fp": fp, "fn": fn,
            "jing_que": round(jing, 3), "zhao_hui": round(zhao, 3),
            "f1": round(f1, 3), "duan_zhao": duan_zhao}


def ni_jian_kong_you_hua(liu):
    if not os.path.exists(JIAN_CE):
        sys.exit("que shao %s, xian yun xing: make ceshi-c" % JIAN_CE)
    shu_ru = "\n".join(" ".join("%.6f" % v for v in hang) for hang in liu) + "\n"
    p = subprocess.run([JIAN_CE, "--shuru"], input=shu_ru, capture_output=True,
                       text=True, timeout=600)
    shijian = []
    for hang in p.stdout.splitlines():
        ge = hang.split("|")
        if len(ge) < 5 or ge[0] not in ("ALARM", "RECOVER"):
            continue
        shijian.append({"t": int(ge[2].split("=")[1]),
                        "dao": int(ge[3][3:]),
                        "dongzuo": ge[0]})
    return shijian


def ni_jian_kong_hua_chuang(liu):
    zong_chang, dao_shu = len(liu), len(liu[0])
    shijian = []
    for j in range(dao_shu):
        chuangkou = [0.0] * CHUANG
        kuan = 0
        guai = False
        for t in range(zong_chang):
            x = liu[t][j]
            if kuan < CHUANG:
                chuangkou[kuan] = x
                kuan += 1
                continue
            jun = sum(chuangkou) / CHUANG
            fang = math.sqrt(sum((v - jun) ** 2 for v in chuangkou) / CHUANG)
            if fang < 1e-9:
                fang = 1e-9
            z = (x - jun) / fang
            if z > 3.0 and not guai:
                guai = True
                shijian.append({"t": t, "dao": j, "dongzuo": "ALARM"})
            elif z < 1.5 and guai:
                guai = False
                shijian.append({"t": t, "dao": j, "dongzuo": "RECOVER"})
            chuangkou.pop(0)
            chuangkou.append(x)
    return shijian


def ni_jian_kong_quan_ju(liu):
    zong_chang, dao_shu = len(liu), len(liu[0])
    shijian = []
    for j in range(dao_shu):
        can_kao = [liu[t][j] for t in range(min(CAN_KAO_CHANG, zong_chang))]
        jun = sum(can_kao) / len(can_kao)
        fang = math.sqrt(sum((v - jun) ** 2 for v in can_kao) / len(can_kao))
        if fang < 1e-9:
            fang = 1e-9
        guai = False
        for t in range(zong_chang):
            z = abs(liu[t][j] - jun) / fang
            if z > 3.0 and not guai:
                guai = True
                shijian.append({"t": t, "dao": j, "dongzuo": "ALARM"})
            elif z < 2.0 and guai:
                guai = False
                shijian.append({"t": t, "dao": j, "dongzuo": "RECOVER"})
    return shijian


def main():
    hui_zong = {"shu_ju": SHU_JU, "tong_dao": TONG_DAO, "fang_fa": {}, "can_zhao": CAN_ZHAO}
    for ming, han_shu, lei in (("优化(自适应四机制)", ni_jian_kong_you_hua, True),
                               ("基线1(滑窗z分数)", ni_jian_kong_hua_chuang, False),
                               ("基线2(全局3西格玛)", ni_jian_kong_quan_ju, False)):
        zong_tp = zong_fp = zong_fn = 0
        tong_dao_biao = {}
        vus_lie = []
        for chan_id in TONG_DAO:
            liu = jia_zai(chan_id)
            biao_qian = du_biao_qian(chan_id)
            shi_jian = han_shu(liu)
            huo = ni_huo_yue_zong(shi_jian, len(liu), len(liu[0]))
            zhi = dian_tiao_zheng(huo, biao_qian)
            tong_dao_biao[chan_id] = zhi
            vus_lie.append(vus_pr_zong(shi_jian, len(liu), len(liu[0]), biao_qian))
            zong_tp += zhi["tp"]
            zong_fp += zhi["fp"]
            zong_fn += zhi["fn"]
        vus_jun = sum(vus_lie) / len(vus_lie)
        jing = zong_tp / (zong_tp + zong_fp) if zong_tp + zong_fp else 0.0
        zhao = zong_tp / (zong_tp + zong_fn) if zong_tp + zong_fn else 0.0
        f1 = 2 * jing * zhao / (jing + zhao) if jing + zhao else 0.0
        hui_zong["fang_fa"][ming] = {
            "zong_f1": round(f1, 3), "zong_jing_que": round(jing, 3),
            "zong_zhao_hui": round(zhao, 3), "wu_bao_dian": zong_fp,
            "tsb_ad_vus_pr": round(vus_jun, 3), "vus_ge_chan": [round(v, 3) for v in vus_lie],
            "tong_dao": tong_dao_biao}
    print("=" * 72)
    print("  SMAP/MSL 公开数据集异常检测对比  通道: %s" % " ".join(TONG_DAO))
    print("=" * 72)
    for ming, zhi in hui_zong["fang_fa"].items():
        print("-- %s --" % ming)
        for chan_id, z in zhi["tong_dao"].items():
            print("  %s: F1=%.3f 精确=%.3f 召回=%.3f 段检出=%d/%d" %
                  (chan_id.ljust(5), z["f1"], z["jing_que"], z["zhao_hui"],
                   z["duan_zhao"], len(du_biao_qian(chan_id))))
        print("  总F1=%.3f 精确=%.3f 召回=%.3f 误报点=%d  TSB-AD VUS-PR=%.3f" %
              (zhi["zong_f1"], zhi["zong_jing_que"], zhi["zong_zhao_hui"],
               zhi["wu_bao_dian"], zhi["tsb_ad_vus_pr"]))
    print("-- 参照系: %s --" % CAN_ZHAO["fang_fa"])
    print("  论文汇总 F1: SMAP=%.2f MSL=%.2f (离线GPU方法, 单通道子集不可直接排名)" %
          (CAN_ZHAO["hui_zong"]["SMAP"], CAN_ZHAO["hui_zong"]["MSL"]))
    print("=" * 72)
    with open(BAO_GAO, "w") as f:
        json.dump(hui_zong, f, ensure_ascii=False, indent=2)
    print("已写入 %s" % BAO_GAO)


if __name__ == "__main__":
    main()
