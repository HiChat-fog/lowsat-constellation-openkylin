import json
import os
import subprocess

import pytest

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUIBI = os.path.join(GEN, "pinggu", "duibi.py")
SMAP_SHUJU = (os.environ.get("WX_SMAP_DIR")
              or os.environ.get("WX_SMAP_SHUJU")
              or os.path.join(os.path.dirname(GEN), "shiyan", "shuju_smap"))
BAO_GAO = "/tmp/weixing_duibi_baogao.json"


class TestZhineng:
    @pytest.mark.skipif(not os.path.exists("/tmp/jz"), reason="xian make ceshi-c gou jian /tmp/jz")
    def test_duibi(self):
        r = subprocess.run(["python3", DUIBI], capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stdout + r.stderr
        with open(BAO_GAO) as f:
            bao = json.load(f)
        yh, jx = bao["you_hua"], bao["ji_xian"]
        assert yh["jian_chu_lv"] == 100.0
        assert yh["wu_bao"] == 0
        assert yh["guo_zao_hui_fu"] == 0
        for jian in ("0_TB", "1_PIAO_YI", "2_FANG_CHA", "3_KA_SI"):
            assert yh["ge_lei"][jian]["jian_chu"], jian
            assert yh["ge_lei"][jian]["lei_zheng"], jian
        assert yh["jian_chu_lv"] > jx["jian_chu_lv"]
        assert yh["wu_bao"] < jx["wu_bao"]
        assert yh["guo_zao_hui_fu"] < jx["guo_zao_hui_fu"]
        assert not jx["ge_lei"]["3_KA_SI"]["jian_chu"]

    @pytest.mark.skipif(not os.path.isdir(SMAP_SHUJU),
                        reason="que SMAP/MSL shu_ju(shiyan/shuju_smap)")
    @pytest.mark.skipif(not os.path.exists("/tmp/jz"), reason="xian make ceshi-c gou jian /tmp/jz")
    def test_smap_duibi(self):
        r = subprocess.run(["python3", os.path.join(GEN, "pinggu", "smap_duibi.py")],
                           capture_output=True, text=True, timeout=1200)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-500:]
        with open("/tmp/weixing_smap_baogao.json") as f:
            bao = json.load(f)
        fang = bao["fang_fa"]
        yh = fang["优化(自适应四机制)"]
        assert yh["zong_f1"] > fang["基线1(滑窗z分数)"]["zong_f1"]
        assert yh["zong_f1"] > fang["基线2(全局3西格玛)"]["zong_f1"]
        assert yh["zong_zhao_hui"] > fang["基线1(滑窗z分数)"]["zong_zhao_hui"]
        assert yh["zong_zhao_hui"] > fang["基线2(全局3西格玛)"]["zong_zhao_hui"]

    @pytest.mark.skipif(not os.path.exists("/tmp/jz"), reason="xian make ceshi-c gou jian /tmp/jz")
    def test_zice_wen_ding(self):
        for _ in range(3):
            r = subprocess.run(["/tmp/jz", "--zice"], capture_output=True, text=True, timeout=60)
            assert r.returncode == 0
            assert "ZICE PASS" in r.stdout
