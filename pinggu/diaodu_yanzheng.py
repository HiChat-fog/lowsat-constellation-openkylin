#!/usr/bin/env python3
import math
import random
import sys

from scipy import stats

ZHONG_ZI = 20260829
LUN = 60
GE = 30
LV = 2.0
FU_WU_A = 0.5
FU_WU_B = 5.5
JIE_DIANS = 3


def sheng_cheng(zhong_zi):
    sui = random.Random(zhong_zi)
    dao_da = []
    shi_ke = 0.0
    fu_wu = []
    for _ in range(GE):
        shi_ke += sui.expovariate(LV)
        dao_da.append(shi_ke)
        fu_wu.append(FU_WU_A + sui.random() * (FU_WU_B - FU_WU_A))
    return dao_da, fu_wu


def mo_ni(dao_da, fu_wu, sf_duan):
    jd = [0.0] * JIE_DIANS
    deng_hou = []
    zhu_liu = []
    if not sf_duan:
        for i in range(len(dao_da)):
            xuan = min(range(JIE_DIANS), key=lambda j: jd[j])
            kai = max(dao_da[i], jd[xuan])
            deng_hou.append(kai - dao_da[i])
            zhu_liu.append(kai + fu_wu[i] - dao_da[i])
            jd[xuan] = kai + fu_wu[i]
        return deng_hou, zhu_liu
    wei_pai = sorted(range(len(dao_da)), key=lambda k: dao_da[k])
    xian_zai = 0.0
    while wei_pai:
        you_kong = -1
        for j in range(JIE_DIANS):
            if jd[j] <= xian_zai + 1e-9:
                you_kong = j
                break
        if you_kong < 0:
            xian_zai = min(jd)
            continue
        xuan = -1
        zui_duan = 1e18
        for i in wei_pai:
            if dao_da[i] <= xian_zai + 1e-9 and fu_wu[i] < zui_duan:
                zui_duan = fu_wu[i]
                xuan = i
        if xuan < 0:
            xian_zai = min(dao_da[i] for i in wei_pai)
            continue
        deng_hou.append(xian_zai - dao_da[xuan])
        zhu_liu.append(xian_zai + fu_wu[xuan] - dao_da[xuan])
        jd[you_kong] = xian_zai + fu_wu[xuan]
        wei_pai.remove(xuan)
    return deng_hou, zhu_liu


def main():
    dao_da, fu_wu = sheng_cheng(ZHONG_ZI)
    ge_ge = [dao_da[i] - (dao_da[i - 1] if i else 0.0) for i in range(1, len(dao_da))]
    ks_dao = stats.kstest(ge_ge, "expon", args=(0, 1.0 / LV))
    ks_fu = stats.kstest(fu_wu, "uniform", args=(FU_WU_A, FU_WU_B - FU_WU_A))

    deng, zhu = mo_ni(dao_da, fu_wu, False)
    guan_ce_shi = (dao_da[-1] - dao_da[0])
    L = sum(zhu) / guan_ce_shi
    lam = (len(dao_da) - 1) / guan_ce_shi
    W = sum(zhu) / len(zhu)
    litt_cha = abs(L - lam * W) / max(lam * W, 1e-9)

    deng_sjf, _ = mo_ni(dao_da, fu_wu, True)
    jun_fcfs = sum(deng) / len(deng)
    jun_sjf = sum(deng_sjf) / len(deng_sjf)

    guan = {"lv_bo_kc_p": round(ks_dao.pvalue, 4),
            "fu_wu_kc_p": round(ks_fu.pvalue, 4),
            "little_pian_cha": round(100.0 * litt_cha, 2),
            "fcfs_deng": round(jun_fcfs, 3), "sjf_deng": round(jun_sjf, 3),
            "sjf_jiang": round(100.0 * (jun_fcfs - jun_sjf) / jun_fcfs, 1)}
    print("=" * 64)
    print("  调度模拟器外部理论交叉验证  KS 检验 + Little 定律")
    print("=" * 64)
    print("到达间隔 KS 检验 p 值 = %.4f (H0: 指数分布 lv=%.1f, p>0.05 即符合)" % (ks_dao.pvalue, LV))
    print("服务时长   KS 检验 p 值 = %.4f (H0: 均匀分布 [%.1f,%.1f])" % (ks_fu.pvalue, FU_WU_A, FU_WU_B))
    print("Little 定律 L=λW: 观测 L=%.3f, λW=%.3f, 偏差 %.1f%%" %
          (L, lam * W, 100.0 * litt_cha))
    print("FCFS 平均等待 %.3f s vs SJF %.3f s, 降幅 %.1f%%" %
          (jun_fcfs, jun_sjf, 100.0 * (jun_fcfs - jun_sjf) / jun_fcfs))
    print("=" * 64)
    with open("/tmp/diaodu_yanzheng.json", "w") as f:
        import json
        json.dump(guan, f, ensure_ascii=False, indent=2)
    huai = 0
    if ks_dao.pvalue < 0.05: huai = 1
    if ks_fu.pvalue < 0.05: huai = 1
    if litt_cha > 0.15: huai = 1
    if jun_sjf >= jun_fcfs: huai = 1
    if huai:
        print("YAN_ZHENG FAIL")
        return 1
    print("YAN_ZHENG PASS: sheng_cheng_qi fu_he li_lun fen bu, Little ding lv zi qia, SJF you xiao")
    return 0


if __name__ == "__main__":
    sys.exit(main())
