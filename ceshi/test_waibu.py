import json
import os
import subprocess

import pytest

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIANCHI_SHUJU = (os.environ.get("WX_DIANCHI_DIR")
                 or os.environ.get("WX_DIANCHI_SHUJU")
                 or os.path.join(os.path.dirname(GEN), "shiyan", "shuju_dianchi"))


class TestWaibu:
    def test_diaodu_yanzheng(self):
        r = subprocess.run(["python3", GEN + "/pinggu/diaodu_yanzheng.py"],
                           capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stdout + r.stderr
        with open("/tmp/diaodu_yanzheng.json") as f:
            bao = json.load(f)
        assert bao["lv_bo_kc_p"] > 0.05
        assert bao["fu_wu_kc_p"] > 0.05
        assert bao["little_pian_cha"] < 15.0
        assert bao["sjf_jiang"] > 10.0

    @pytest.mark.skipif(not os.path.isdir(DIANCHI_SHUJU),
                        reason="que NASA dianchi shu_ju(shiyan/shuju_dianchi)")
    def test_dianchi_yanzheng(self):
        r = subprocess.run(["python3", GEN + "/pinggu/dianchi_yanzheng.py"],
                           capture_output=True, text=True, timeout=600)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-500:]
        with open("/tmp/weixing_dianchi_baogao.json") as f:
            bao = json.load(f)
        assert bao["dian_chi"], "wu you_xiao dian_chi shu_ju"
        for ming, z in bao["dian_chi"].items():
            assert z["jun_xiang_dui_wu_cha"] <= 0.30, (ming, z)
            assert z["xun_huan_shu"] >= 100

    def test_smap_vus_pr(self):
        lu = "/tmp/weixing_smap_baogao.json"
        if not os.path.exists(lu):
            pytest.skip("xian yun xing smap_duibi")
        with open(lu) as f:
            bao = json.load(f)
        assert "can_zhao" in bao and bao["can_zhao"]["lai_yuan"].startswith("Hundman")
        for m, z in bao["fang_fa"].items():
            assert "tsb_ad_vus_pr" in z, m
        yh = bao["fang_fa"]["优化(自适应四机制)"]
        assert yh["zong_f1"] >= bao["fang_fa"]["基线1(滑窗z分数)"]["zong_f1"]
        assert yh["zong_zhao_hui"] > bao["fang_fa"]["基线2(全局3西格玛)"]["zong_zhao_hui"]

    @pytest.mark.skipif(not os.path.exists(os.path.join(GEN, "waibu", "tsb_ad", "LICENSE")),
                        reason="que TSB-AD vendor mu_lu")
    def test_tsb_ad_vendor(self):
        assert os.path.exists(GEN + "/waibu/tsb_ad/evaluation/metrics.py")
        with open(GEN + "/waibu/tsb_ad/LICENSE") as f:
            assert "Apache License" in f.read()
