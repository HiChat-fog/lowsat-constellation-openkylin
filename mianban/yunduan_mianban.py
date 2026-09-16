#!/usr/bin/env python3
import glob
import json
import os
import sys
import time

import sqlite3 as sq

SHUJU = "/tmp/qemu_env/share/shuju"
KULU = os.environ.get("WX_KU", "")
XING = {1: "weixing1", 2: "weixing2", 3: "weixing3"}


def du_yunduan_peizhi():
    global SHUJU, XING
    lu = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "peizhi", "yunduan.conf")
    ming_lie = []
    try:
        with open(lu) as f:
            for hang in f:
                if "=" not in hang or hang.strip().startswith("#"):
                    continue
                ming, zhi = hang.split("=", 1)
                ming, zhi = ming.strip(), zhi.strip()
                if ming == "shuju":
                    SHUJU = zhi
                elif ming:
                    ming_lie.append(ming)
    except Exception:
        pass
    if os.environ.get("WX_SHUJU"):
        SHUJU = os.environ["WX_SHUJU"]
    if ming_lie:
        XING = dict(enumerate(sorted(ming_lie), 1))


du_yunduan_peizhi()

def du_xin(xing):
    ku_jie = os.path.join(SHUJU, xing + ".db")
    try:
        if os.path.exists(ku_jie):
            k = sq.connect(ku_jie)
            hang = k.execute("SELECT duc FROM guance WHERE jiedian=? ORDER BY id DESC LIMIT 1", (xing,)).fetchone()
            k.close()
            if hang:
                return json.loads(hang[0]), os.path.getmtime(ku_jie)
    except Exception:
        pass
    try:
        if KULU and os.path.exists(KULU):
            k = sq.connect(KULU)
            hang = k.execute("SELECT duc FROM guance WHERE jiedian=? ORDER BY id DESC LIMIT 1", (xing,)).fetchone()
            k.close()
            if hang:
                return json.loads(hang[0]), os.path.getmtime(KULU)
    except Exception:
        pass
    try:
        lu = os.path.join(SHUJU, xing + ".json")
        xiugai = os.path.getmtime(lu)
        with open(lu) as f:
            hang = [h for h in f.read().strip().splitlines() if h.startswith("{")]
        if not hang:
            return None, None
        return json.loads(hang[-1]), xiugai
    except Exception:
        return None, None

def du_shijian_file(xing):
    lu = os.path.join(SHUJU, xing + ".shijian")
    try:
        with open(lu) as f:
            hang = [h for h in f.read().strip().splitlines() if h.startswith("ALARM")]
        return hang[-1] if hang else None
    except Exception:
        return None

def zhuangtai_biaoji(xin, xiugai):
    if xin is None:
        return "失联"
    if time.time() - xiugai > 15:
        return "失联"
    if xin.get("cpu", 0) > 85 or xin.get("neicun", 0) > 85:
        return "告警"
    return "正常"

def yifu(xin, key):
    if not xin or key not in xin:
        return "-"
    try:
        return "%.1f%%" % xin[key]
    except Exception:
        return str(xin[key])

def shou_ming(shou):
    if not shou:
        return "-"
    return "%s(%s)" % (shou[0].get("ming", "?"), shou[0].get("haoshi_ms", 0) if "haoshi_ms" in shou[0] else shou[0].get("ci", 0))

def jingbao(xing):
    ba = du_shijian_file(xing)
    if ba:
        return ba
    lu = os.path.join(SHUJU, xing + ".json")
    try:
        with open(lu) as f:
            lines = [l for l in f.read().strip().splitlines() if l.startswith("ALARM")]
        if lines:
            return lines[-1]
    except Exception:
        pass
    return None

def du_renwu():
    xin = []
    for lu in sorted(glob.glob(os.path.join(SHUJU, "renwu_*.json"))):
        try:
            with open(lu) as f:
                hang = [h for h in f.read().strip().splitlines() if h.startswith("{")]
            if hang:
                xin.append(hang[-1])
        except Exception:
            pass
    return xin[-3:]


def hua():
    os.system("clear")
    shijian = time.strftime("%H:%M:%S")
    print("=" * 78)
    print("  低轨卫星星座运行保障平台 - 云端观测面板   %s" % shijian)
    print("=" * 78)
    print("%-10s %-6s %-8s %-8s %-10s %-10s %-10s %-6s" %
          ("节点", "状态", "CPU", "内存", "总syscall", "切换", "算力榜首", "事件"))
    print("-" * 78)
    for hao in sorted(XING):
        ming = XING[hao]
        xin, xiugai = du_xin(ming)
        zhuangtai = zhuangtai_biaoji(xin, xiugai)
        if xin:
            zong = xin.get("zong_sys", 0)
            qiehuan = xin.get("qiehuan_zeng", xin.get("qiehuan", 0))
            suan = shou_ming(xin.get("suanli_top"))
            ba = jingbao(ming)
            shijian_col = "!"
            if ba:
                shijian_col = "*"
            print("%-10s %-6s %-8s %-8s %-10d %-10d %-10s %-6s" %
                  (ming, zhuangtai, yifu(xin, "cpu"), yifu(xin, "neicun"),
                   zong, qiehuan, suan[:10], shijian_col))
            if ba:
                print("    └─ %s" % ba[:60])
        else:
            print("%-10s %-6s" % (ming, zhuangtai))
    print("-" * 78)
    print("最近任务:")
    for h in du_renwu():
        try:
            g = json.loads(h)
            print("  %s %s@%s 执行%dms 来源%s" %
                  (g.get("wancheng", "-"), g.get("renwu", "-"), g.get("jiedian", "-"),
                   g.get("hao_shi_ms", 0), g.get("laiyuan", "-")))
        except Exception:
            pass
    print("图例: * 有告警   ! 有时间戳  状态失联=15秒无上报")
    print("=" * 78)

if __name__ == "__main__":
    try:
        while True:
            hua()
            time.sleep(2)
    except KeyboardInterrupt:
        print("面板退出")