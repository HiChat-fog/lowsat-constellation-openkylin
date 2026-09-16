#!/usr/bin/env python3
import os
import re
import subprocess
import sys

MU = os.path.dirname(os.path.abspath(__file__))
BU_ZOU = ["fuwu_caijian3.py", "caijian_rm.py", "caijian_shishi.py", "caijian_shendu.py", "ce_caijian_mem.py"]
DF_GE = re.compile(r"/dev\S+\s+\S+\s+([0-9.]+[KMG]?)\s+[0-9.]+[KMG]?\s+\d+%\s+/")


def dan_wei_zhi(s):
    dan = {"K": 1, "M": 2, "G": 3}
    if s[-1].isdigit():
        return float(s)
    return float(s[:-1]) * (1024 ** dan.get(s[-1], 1))


def main():
    ji_xian = "/tmp/openkylin-2.0-sp2-rc1-qemu-rva23.img"
    xin_jing = "/tmp/qemu_env/caijian_xin.qcow2"
    if not os.path.exists(ji_xian):
        print("[!!] que shao ji xian jing xiang: %s (xian yun xing jiaoben/zhu_bei.sh)" % ji_xian)
        sys.exit(1)
    if os.path.exists(xin_jing):
        os.remove(xin_jing)
    p = subprocess.run(["qemu-img", "create", "-f", "qcow2", "-b", ji_xian, "-F", "raw", xin_jing],
                       capture_output=True, text=True)
    if p.returncode != 0:
        print("[!!] chuang jian gan jing ji xian shi bai:", p.stderr[-300:])
        sys.exit(1)
    os.environ["WX_QCOW2"] = "caijian_xin"
    print("=== gan jing ji xian: %s (yuan shi jing xiang de du li overlay) ===" % xin_jing, flush=True)
    df_xing = []
    for bu in BU_ZOU:
        print("=== %s ===" % bu, flush=True)
        try:
            p = subprocess.run([sys.executable, os.path.join(MU, bu)],
                               capture_output=True, text=True, timeout=7200)
        except subprocess.TimeoutExpired:
            print("[!!] %s chao shi" % bu)
            sys.exit(1)
        sys.stdout.write(p.stdout[-2000:])
        shu = DF_GE.findall(p.stdout)
        df_xing.extend((bu, float(dan_wei_zhi(n))) for n in shu)
        if p.returncode != 0 or "EXC:" in p.stdout:
            print("[!!] %s shi_bai" % bu)
            sys.exit(1)
    if len(df_xing) >= 2:
        ji_xian, zui_hou = df_xing[0][1], df_xing[-1][1]
        jiang = 100.0 * (ji_xian - zui_hou) / ji_xian if ji_xian > 0 else 0.0
        print("=" * 60)
        print("  镜像根分区占用: 基线 %.1f GB -> 裁剪后 %.1f GB  降幅 %.1f%%(要求>=20%%)"
              % (ji_xian / 1024 ** 3, zui_hou / 1024 ** 3, jiang))
        print("=" * 60)
    else:
        print("[!!] wei shou ji dao zu gou de df yang ben, wu fa hui zong")
        sys.exit(1)


if __name__ == "__main__":
    main()
