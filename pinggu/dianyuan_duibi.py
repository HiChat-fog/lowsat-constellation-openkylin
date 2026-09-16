#!/usr/bin/env python3
import json
import os
import subprocess
import sys

DY = os.environ.get("WX_DIAN_YUAN", "/tmp/dy")
JZ = os.environ.get("WX_JIAN_CE", "/tmp/jz")
BAO_GAO = os.environ.get("WX_DY_BAOGAO", "/tmp/weixing_dianyuan_baogao.json")
ZHANG = 2000

GUAN_LIAN = {
    "MUXIAN_DIELUO": {0},
    "DIANCHI_NEIZU": {1, 2},
    "GUANGFU_SHUAIJIAN": {4},
    "CHONGDIAN_SHIXIAO": {2},
    "GUOWEN": {5},
    "SEU": set(),
}


def yun(ming_ling, shu_ru=None):
    p = subprocess.run(ming_ling, input=shu_ru, capture_output=True, text=True, timeout=300)
    return p.stdout, p.stderr


jie_xi_zhen = os.path.dirname(os.path.abspath(__file__))


def fen_xi(yuan, shi_jian_hang, biao_ji):
    duan = [b for b in biao_ji if b["leixing"] in GUAN_LIAN and b["leixing"] != "SEU"]
    guo_du = [b for b in biao_ji if b["leixing"] == "GUODU"]
    if yuan == "ling_yu":
        bao = []
        for h in shi_jian_hang:
            ge = h.split("|")
            if ge[0] == "ALARM" and "leixing=DIANYU" in h:
                t = int(ge[2].split("=")[1])
                biao = ge[5].split("=")[1].strip()
                dao = ge[4].split("=")[1]
                bao.append((t, biao, dao))
    else:
        bao = []
        for h in shi_jian_hang:
            ge = h.split("|")
            if ge[0] == "ALARM" and len(ge) > 4 and ge[4].startswith("leixing="):
                t = int(ge[2].split("=")[1])
                dao = int(ge[3][3:]) if ge[3].startswith("dao") else -1
                bao.append((t, ge[4].split("=")[1], dao))
    zhao = {}
    for b in duan:
        tong = GUAN_LIAN[b["leixing"]]
        nei = [x for x in bao if x[0] >= b["kaishi"] - 2 and x[0] <= b["jieshu"] + 80
               and (x[2] in tong if isinstance(x[2], int) else x[1] == b["leixing"])]
        zhao[b["leixing"]] = bool(nei)
    guo_bao = sum(1 for x in bao
                  if x[1] != "GUANGFU_SHUAIJIAN"
                  and any(g["kaishi"] - 2 <= x[0] <= g["jieshu"] for g in guo_du))
    gan_jing = [x for x in bao
                if not any(g["kaishi"] - 2 <= x[0] <= g["jieshu"] for g in guo_du)
                and not any(b["kaishi"] - 2 <= x[0] <= b["jieshu"] + 80 for b in duan)]
    return {"duan_jian_chu": sum(1 for b in duan if zhao[b["leixing"]]),
            "duan_zong": len(duan),
            "guo_du_wu_bao": guo_bao,
            "qi_ta_wu_bao": len(gan_jing),
            "zhao": zhao}


def main():
    if not os.path.exists(DY) or not os.path.exists(JZ):
        sys.exit("que shao %s huo %s, xian make" % (DY, JZ))
    csv, cuo = yun([DY, "--moxing", str(ZHANG)])
    biao_ji = []
    for h in cuo.splitlines():
        ge = h.split("|")
        if ge[0] != "BIAOJI":
            continue
        biao_ji.append({"leixing": ge[1].split("=")[1],
                        "kaishi": int(ge[2].split("=")[1]),
                        "jieshu": int(ge[3].split("=")[1])})
    shu_ru = csv + "\n" if not csv.endswith("\n") else csv
    jz_chu, _ = yun([JZ, "--shuru"], shu_ru)
    dy_chu, _ = yun([DY, "--shuru"], shu_ru)
    tong_yong = fen_xi("tong_yong", jz_chu.splitlines(), biao_ji)
    ling_yu = fen_xi("ling_yu", dy_chu.splitlines(), biao_ji)
    zui_zhou = [h for h in dy_chu.splitlines() if h.startswith("ZUIZHOU")]
    soh = rul = None
    if zui_zhou:
        for xiang in zui_zhou[0].split("|")[1:]:
            if xiang.startswith("soh="):
                soh = float(xiang[4:])
            if xiang.startswith("rul="):
                rul = float(xiang[4:])
    seu_yao = any(h.startswith("SEU|") for h in dy_chu.splitlines())
    bao = {"zhang": ZHANG, "tong_yong": tong_yong, "ling_yu": ling_yu,
           "soh": soh, "rul": rul, "seu": seu_yao}
    print("=" * 72)
    print("  电源系统领域层对比评估  通用四机制引擎(原始通道) vs 领域层(归一化+语义)")
    print("=" * 72)
    for ming, zhi in (("通用引擎(原始通道)", tong_yong), ("领域层(归一化+语义)", ling_yu)):
        print("-- %s --" % ming)
        for lei, zhao in zhi["zhao"].items():
            print("  %s: %s" % (lei.ljust(18), "jian_chu" if zhao else "lou_jian"))
        print("  段检出=%d/%d  瞬态误报=%d  其他误报=%d" %
              (zhi["duan_jian_chu"], zhi["duan_zong"], zhi["guo_du_wu_bao"], zhi["qi_ta_wu_bao"]))
    print("领域层 SOH=%.1f RUL=%.0f SEU事件=%s" % (soh, rul, seu_yao))
    print("=" * 72)
    with open(BAO_GAO, "w") as f:
        json.dump(bao, f, ensure_ascii=False, indent=2)
    print("已写入 %s" % BAO_GAO)


if __name__ == "__main__":
    main()
