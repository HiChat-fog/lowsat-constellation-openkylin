#!/usr/bin/env python3
import glob
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3 as sq

DUAN_KOU = int(os.environ.get("WX_PROM_DUAN", "9113"))
SHUJU = "/tmp/qemu_env/share/shuju"
XIN_XIAN = 20


def du_yun_duan_pei_zhi():
    global SHUJU
    lu = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "peizhi", "yunduan.conf")
    try:
        with open(lu) as f:
            for hang in f:
                if "=" in hang and not hang.strip().startswith("#"):
                    ming, zhi = hang.split("=", 1)
                    if ming.strip() == "shuju":
                        SHUJU = zhi.strip()
    except Exception:
        pass
    if os.environ.get("WX_SHUJU"):
        SHUJU = os.environ["WX_SHUJU"]


du_yun_duan_pei_zhi()


def du_jie_dian():
    jie = set()
    for lu in glob.glob(os.path.join(SHUJU, "*.json")):
        jie.add(os.path.basename(lu)[:-5])
    for lu in glob.glob(os.path.join(SHUJU, "*.db")):
        jie.add(os.path.basename(lu)[:-3])
    return sorted(jie)


def du_zui_xin(jie):
    lu = os.path.join(SHUJU, jie + ".db")
    if os.path.exists(lu):
        try:
            k = sq.connect(lu)
            hang = k.execute("SELECT duc, unixepoch(shijian) FROM guance "
                             "ORDER BY id DESC LIMIT 1").fetchone()
            k.close()
            if hang:
                return json.loads(hang[0]), hang[1]
        except Exception:
            pass
    try:
        lu = os.path.join(SHUJU, jie + ".json")
        xiugai = os.path.getmtime(lu)
        with open(lu) as f:
            hang = [h for h in f.read().strip().splitlines() if h.startswith("{")]
        if hang:
            return json.loads(hang[-1]), xiugai
    except Exception:
        pass
    return None, None


JIA_ZU = [
    ("weixing_up", "gauge", "节点遥测新鲜度(1=上报正常)"),
    ("weixing_yaoce_lao_zui_jin", "gauge", "遥测距今年龄秒"),
    ("weixing_cpu_baifen", "gauge", "CPU 占用百分比"),
    ("weixing_neicun_baifen", "gauge", "内存占用百分比"),
    ("weixing_xitong_diaoyong_zong", "counter", "系统调用累计"),
    ("weixing_tiaodu_qie_huan_zong", "counter", "调度切换累计"),
    ("weixing_suanli_shou_hao_ms", "gauge", "算力榜首进程耗时毫秒"),
]


def chan_zhi_biao():
    jia = []
    zhi = []
    now = time.time()
    for jie in du_jie_dian():
        xin, ts = du_zui_xin(jie)
        lao = now - ts if ts else -1
        up = "1" if (xin and 0 <= lao < XIN_XIAN) else "0"
        zhi.append('weixing_up{jiedian="%s"} %s' % (jie, up))
        if xin is None:
            continue
        zhi.append('weixing_yaoce_lao_zui_jin{jiedian="%s"} %.0f' % (jie, lao))
        if "cpu" in xin:
            zhi.append('weixing_cpu_baifen{jiedian="%s"} %.2f' % (jie, xin.get("cpu", 0)))
        if "neicun" in xin:
            zhi.append('weixing_neicun_baifen{jiedian="%s"} %d' % (jie, xin.get("neicun", 0)))
        if "zong_sys" in xin:
            zhi.append('weixing_xitong_diaoyong_zong{jiedian="%s"} %d' %
                       (jie, xin.get("zong_sys", 0)))
        if "qiehuan" in xin:
            zhi.append('weixing_tiaodu_qie_huan_zong{jiedian="%s"} %d' %
                       (jie, xin.get("qiehuan", 0)))
        suan = (xin.get("suanli_top") or [None])[0]
        if suan and "haoshi_ms" in suan:
            zhi.append('weixing_suanli_shou_hao_ms{jiedian="%s", jincheng="%s"} %.0f' %
                       (jie, suan.get("ming", "?"), suan.get("haoshi_ms", 0)))
    for ming, lei, shuo in JIA_ZU:
        jia.append("# HELP %s %s" % (ming, shuo))
        jia.append("# TYPE %s %s" % (ming, lei))
    return "\n".join(jia + zhi) + "\n"


class qi(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        try:
            nei = chan_zhi_biao()
        except Exception as e:
            nei = "# bao_cuo %s\n" % e
        zi = nei.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(zi)))
        self.end_headers()
        self.wfile.write(zi)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    fu = HTTPServer(("0.0.0.0", DUAN_KOU), qi)
    print("prometheus dao chu qi qi dong :%d/metrics  shu_ju_mu=%s" % (DUAN_KOU, SHUJU), flush=True)
    fu.serve_forever()
