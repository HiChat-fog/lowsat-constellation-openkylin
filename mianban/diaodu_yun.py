#!/usr/bin/env python3
import glob
import json
import os
import socket
import time

SHUJU = "/tmp/qemu_env/share/shuju"
DUANKOU = {"weixing1": 8011, "weixing2": 8012, "weixing3": 8013}
XING = ["weixing1", "weixing2", "weixing3"]
LING_PAI_PEI = ""
SHI_BAI = {}
SHI_BAI_BI_KAI = 30


def du_yunduan_peizhi():
    global SHUJU, DUANKOU, XING, LING_PAI_PEI
    lu = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "peizhi", "yunduan.conf")
    try:
        with open(lu) as f:
            for hang in f:
                if "=" not in hang or hang.strip().startswith("#"):
                    continue
                ming, zhi = hang.split("=", 1)
                ming, zhi = ming.strip(), zhi.strip()
                if ming == "shuju":
                    SHUJU = zhi
                elif ming == "ling_pai":
                    LING_PAI_PEI = zhi
                elif ming:
                    DUANKOU[ming] = int(zhi)
    except Exception:
        pass
    if os.environ.get("WX_SHUJU"):
        SHUJU = os.environ["WX_SHUJU"]
    XING = sorted(DUANKOU)


du_yunduan_peizhi()
SHIXIAN = 15
ZHOUQI = 3
CHAOSHI = int(os.environ.get("WX_CHAOSHI", "45") or 45)
LEIXING = ["yaogan_shaixuan", "mubiao_shibie", "zhuangtai_fenxi"]
MUBIAO = []
XUHAO = 0
LING_PAI = os.environ.get("WX_LING_PAI", "") or LING_PAI_PEI
CELUE = os.environ.get("WX_CELUE", "SJF").upper()
BAOFA_SHU = int(os.environ.get("WX_BAOFASHU", "0") or 0)
BAOFA_BEI = int(os.environ.get("WX_BAOFASHU_BEI", "1") or 1)
PAIFA_LUN_QI = int(os.environ.get("WX_PAIFA_LUN_QI", "4") or 4)
PAIFA_MEI_LUN = int(os.environ.get("WX_PAIFA_MEI_LUN", "2") or 2)


def da_yin(xin):
    print(time.strftime("%H:%M:%S|") + xin, flush=True)


def dai_pai_lie():
    dai = [r for r in MUBIAO if r["mubiao"] is None]
    if CELUE == "FCFS":
        return dai
    return sorted(dai, key=lambda r: r["renwu"].get("canliang", 0))


def taizhang_lu():
    return os.path.join(SHUJU, "diaodu_taizhang.json")


def xie_taizhang():
    try:
        with open(taizhang_lu(), "w") as f:
            json.dump({"xuhao": XUHAO, "renwu_lie": MUBIAO}, f)
    except Exception:
        pass


def du_taizhang():
    global XUHAO
    try:
        with open(taizhang_lu()) as f:
            tai = json.load(f)
        XUHAO = tai.get("xuhao", 0)
        MUBIAO.clear()
        MUBIAO.extend(tai.get("renwu_lie", []))
        return True
    except Exception:
        return False


def fa_song(xing, bao):
    bao = dict(bao)
    bao["ling_pai"] = LING_PAI
    try:
        s = socket.create_connection(("127.0.0.1", DUANKOU[xing]), timeout=5)
        s.sendall((json.dumps(bao) + "\n").encode())
        hui = s.recv(128).decode()
        s.close()
        return json.loads(hui)
    except Exception:
        return None


def song_renwu(xing, renwu):
    hui = fa_song(xing, {"mingling": "PAIFA", "renwu": renwu})
    if not hui or "OK" not in hui.get("jieguo", ""):
        if hui and hui.get("jieguo") == "MAN":
            return False, "MAN"
        SHI_BAI[xing] = time.time()
        return False, hui.get("zhuangtai", "DUANKAI") if hui else "DUANKAI"
    SHI_BAI.pop(xing, None)
    return True, hui.get("zhuangtai", "XIN")


def wen_renwu(xing, bianhao):
    hui = fa_song(xing, {"mingling": "CHA", "bianhao": bianhao})
    if not hui or hui.get("jieguo") != "OK":
        return "BU_DA"
    return hui.get("zhuangtai", "MEI_YOU")


def xin_renwu():
    global XUHAO
    XUHAO += 1
    return {"bianhao": "rw-%d" % XUHAO,
            "ming": LEIXING[(XUHAO - 1) % len(LEIXING)],
            "canliang": 200000 + ((XUHAO * 37) % 4) * 100000,
            "chang_shi": 1}


def paifa():
    dai = dai_pai_lie()
    if dai and chong_shi(dai[0]):
        return
    if BAOFA_SHU > 0:
        return
    renwu = xin_renwu()
    mubiao, fuzai = zui_xian()
    if mubiao:
        hao, zhuang = song_renwu(mubiao, renwu)
        if hao:
            MUBIAO.append({"renwu": renwu, "mubiao": mubiao, "huan": time.time(), "chu": time.time()})
            da_yin("派发|%s|%s|%s|负载%.1f%s" % (renwu["bianhao"], mubiao, renwu["ming"], fuzai,
                                               "" if zhuang == "XIN" else "|%s" % zhuang))
            xie_taizhang()
            return
        MUBIAO.append({"renwu": renwu, "mubiao": None, "huan": time.time(), "chu": time.time()})
        da_yin("入列|%s|派往%s失败(%s),挂起待发" % (renwu["bianhao"], mubiao, zhuang))
        xie_taizhang()
        return
    MUBIAO.append({"renwu": renwu, "mubiao": None, "huan": time.time(), "chu": time.time()})
    da_yin("入列|%s|暂无可用节点,台账挂起待发" % renwu["bianhao"])
    xie_taizhang()


def du_jieguo():
    geng = False
    for lu in sorted(glob.glob(os.path.join(SHUJU, "renwu_*.json"))):
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
            bh = g.get("renwu")
            for i in range(len(MUBIAO) - 1, -1, -1):
                ren = MUBIAO[i]
                if ren["renwu"]["bianhao"] == bh:
                    MUBIAO.pop(i)
                    geng = True
                    laiyuan = g.get("laiyuan", "ZHIJIE")
                    zong = time.time() - ren["chu"]
                    if laiyuan == "JIEGUAN":
                        da_yin("星间接管完成|%s|执行节点%s|执行%dms|云端观测全程%.1f秒(要求<=60)"
                               % (bh, g.get("jiedian", "?"), g.get("hao_shi_ms", 0), zong))
                    else:
                        da_yin("完成|%s|%s|执行%dms|全程%.1f秒"
                               % (bh, g.get("jiedian", "?"), g.get("hao_shi_ms", 0), zong))
    if geng:
        xie_taizhang()


def chong_shi(ren, yuan=None):
    paichu = (yuan,) if yuan else ()
    mubiao, fuzai = zui_xian(paichu=paichu)
    if not mubiao:
        return False
    if yuan:
        zhuang = wen_renwu(mubiao, ren["renwu"]["bianhao"])
        if zhuang == "YI_WAN":
            da_yin("销账|%s|CHA对账已在%s完成,不再重派" % (ren["renwu"]["bianhao"], mubiao))
            MUBIAO.remove(ren)
            return True
        if zhuang == "ZAI_PAO":
            da_yin("对账|%s|%s已在执行,继续跟踪" % (ren["renwu"]["bianhao"], mubiao))
            ren["huan"] = time.time()
            return True
    ren["renwu"]["chang_shi"] = ren["renwu"].get("chang_shi", 1) + 1
    hao, zhuang = song_renwu(mubiao, ren["renwu"])
    if zhuang == "YIWAN":
        da_yin("销账|%s|已在%s完成,不再重派" % (ren["renwu"]["bianhao"], mubiao))
        MUBIAO.remove(ren)
        return True
    if hao:
        ren["mubiao"] = mubiao
        ren["huan"] = time.time()
        if yuan:
            da_yin("云端迁移|%s|离开%s|重派%s|中断%.1f秒"
                   % (ren["renwu"]["bianhao"], yuan, mubiao, time.time() - ren["chu"]))
        else:
            da_yin("派发|%s|%s|%s|负载%.1f|待发%.1f秒"
                   % (ren["renwu"]["bianhao"], mubiao, ren["renwu"]["ming"],
                      fuzai, time.time() - ren["chu"]))
        return True
    return False


def jiancha_yi():
    geng = False
    dai = dai_pai_lie()
    qita = [r for r in MUBIAO if r["mubiao"] is not None]
    for ren in dai + qita:
        if ren not in MUBIAO:
            continue
        if ren["mubiao"] is None:
            if chong_shi(ren):
                geng = True
            continue
        fuzai, xiugai = du_fuzai(ren["mubiao"])
        shiqu = fuzai is None or time.time() - xiugai > SHIXIAN
        chaoshi = time.time() - ren["huan"] > CHAOSHI
        if not shiqu and not chaoshi:
            continue
        if chong_shi(ren, yuan=ren["mubiao"]):
            geng = True
        elif chaoshi:
            ren["mubiao"] = None
            geng = True
            da_yin("回列|%s|暂无可用迁移节点,转待发" % ren["renwu"]["bianhao"])
    if geng:
        xie_taizhang()


def dui_zhang():
    geng = False
    for ren in list(MUBIAO):
        if ren["mubiao"] is None:
            continue
        bh = ren["renwu"]["bianhao"]
        zhuang = wen_renwu(ren["mubiao"], bh)
        if zhuang == "ZAI_PAO":
            ren["huan"] = time.time()
            da_yin("对账|%s|%s仍在执行,继续跟踪" % (bh, ren["mubiao"]))
        elif zhuang == "YI_WAN":
            MUBIAO.remove(ren)
            geng = True
            da_yin("对账|%s|%s已完成,台账销账" % (bh, ren["mubiao"]))
        else:
            yuan = ren["mubiao"]
            if not chong_shi(ren, yuan=yuan):
                ren["mubiao"] = None
                da_yin("对账|%s|%s不可达且无处可派,转待发" % (bh, yuan))
            geng = True
    xie_taizhang()


def du_fuzai(xing):
    lu = os.path.join(SHUJU, xing + ".json")
    try:
        xiugai = os.path.getmtime(lu)
        with open(lu) as f:
            hang = [h for h in f.read().strip().splitlines() if h.startswith("{\"shijian\"")]
        if not hang:
            return None, None
        xin = json.loads(hang[-1])
        if "cpu" not in xin or "neicun" not in xin or "qiehuan" not in xin:
            return None, None
        qiehuan_huo = xin.get("qiehuan_zeng", xin.get("qiehuan", 0))
        fuzai = xin.get("cpu", 0) * 0.6 + min(qiehuan_huo / 100.0, 100.0) * 0.2 + xin.get("neicun", 0) * 0.2
        return fuzai, xiugai
    except Exception:
        return None, None


def zui_xian(paichu=()):
    zui = None
    zui_zhi = 1e18
    for ming in XING:
        if ming in paichu:
            continue
        if time.time() - SHI_BAI.get(ming, 0) < SHI_BAI_BI_KAI:
            continue
        fuzai, xiugai = du_fuzai(ming)
        if fuzai is None or time.time() - xiugai > SHIXIAN:
            continue
        if fuzai < zui_zhi:
            zui_zhi = fuzai
            zui = ming
    return zui, zui_zhi


def zhuangtai():
    xian = []
    for ming in XING:
        fuzai, xiugai = du_fuzai(ming)
        if fuzai is None or time.time() - xiugai > SHIXIAN:
            xian.append("%s:失联" % ming)
        else:
            xian.append("%s:%.1f" % (ming, fuzai))
    dai = sum(1 for r in MUBIAO if r["mubiao"] is None)
    print(time.strftime("%H:%M:%S|") + "状态|" + " ".join(xian) + "|在途任务%d|待发%d" % (len(MUBIAO) - dai, dai),
          flush=True)


def main():
    if du_taizhang():
        print("台账恢复:%d 个任务,xuhao=%d" % (len(MUBIAO), XUHAO), flush=True)
    dui_zhang()
    if BAOFA_SHU > 0:
        for _ in range(BAOFA_SHU):
            rw = xin_renwu()
            if BAOFA_BEI > 1:
                rw["canliang"] = rw["canliang"] * BAOFA_BEI
            MUBIAO.append({"renwu": rw, "mubiao": None, "huan": time.time(), "chu": time.time()})
        xie_taizhang()
        da_yin("突发负载|%d 个任务入队|策略%s|canliang倍率%d" % (BAOFA_SHU, CELUE, BAOFA_BEI))
    lunci = 0
    while True:
        lunci += 1
        zhuangtai()
        du_jieguo()
        if lunci % PAIFA_LUN_QI == 0:
            for _ in range(PAIFA_MEI_LUN):
                paifa()
        jiancha_yi()
        time.sleep(ZHOUQI)


if __name__ == "__main__":
    main()
