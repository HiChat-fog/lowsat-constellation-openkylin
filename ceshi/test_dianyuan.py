import json
import os
import subprocess

import pytest

DY = "/tmp/dy"
GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUIBI = os.path.join(GEN, "pinggu", "dianyuan_duibi.py")
BAO_GAO = "/tmp/weixing_dianyuan_baogao.json"


class TestDianyuan:
    @pytest.mark.skipif(not os.path.exists(DY), reason="xian make chengwu/dianyuan bing fu zhi /tmp/dy")
    def test_zice(self):
        for _ in range(2):
            r = subprocess.run([DY, "--zice"], capture_output=True, text=True, timeout=120)
            assert r.returncode == 0
            assert "ZICE PASS" in r.stdout

    @pytest.mark.skipif(not (os.path.exists(DY) and os.path.exists("/tmp/jz")),
                        reason="xian make bing fu zhi /tmp/dy /tmp/jz")
    def test_duibi(self):
        r = subprocess.run(["python3", DUIBI], capture_output=True, text=True, timeout=600)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-500:]
        with open(BAO_GAO) as f:
            bao = json.load(f)
        ly, ty = bao["ling_yu"], bao["tong_yong"]
        assert ly["duan_jian_chu"] == ly["duan_zong"] == 5
        assert ly["guo_du_wu_bao"] == 0
        assert ly["guo_du_wu_bao"] < ty["guo_du_wu_bao"]
        assert ly["duan_jian_chu"] >= ty["duan_jian_chu"]
        assert ty["guo_du_wu_bao"] > 0
        for lei in ("MUXIAN_DIELUO", "DIANCHI_NEIZU", "GUANGFU_SHUAIJIAN",
                    "CHONGDIAN_SHIXIAO", "GUOWEN"):
            assert ly["zhao"][lei], lei
        assert 40.0 <= bao["soh"] <= 95.0
        assert bao["rul"] > 0
        assert bao["seu"]

    @pytest.mark.skipif(not os.path.exists(DY), reason="xian make chengwu/dianyuan")
    def test_shuru_guan_dao(self):
        mo = subprocess.run([DY, "--moxing", "800"], capture_output=True, text=True, timeout=120)
        assert mo.returncode == 0
        assert len(mo.stdout.splitlines()) == 800
        sh = subprocess.run([DY, "--shuru"], input=mo.stdout, capture_output=True, text=True, timeout=120)
        assert sh.returncode == 0
        assert "ZUIZHOU|soh=" in sh.stdout
        zhi = dict(x.split("=") for x in sh.stdout.strip().splitlines()[-1].split("|")[1:])
        assert 0.0 <= float(zhi["soh"]) <= 100.0
        assert int(zhi["xunhuan"]) >= 1
