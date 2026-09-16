import subprocess
import os

import pytest

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestCzijian:
    @pytest.mark.skipif(not os.path.exists("/tmp/jz"), reason="xian make ceshi-c gou jian /tmp/jz")
    def test_jiance(self):
        r = subprocess.run(["/tmp/jz", "--zice"], capture_output=True, text=True)
        assert r.returncode == 0
        assert "ZICE PASS" in r.stdout

    @pytest.mark.skipif(not os.path.exists("/tmp/dz"), reason="xian make ceshi-c gou jian /tmp/dz")
    def test_diaodu(self):
        r = subprocess.run(["/tmp/dz", "--zice"], capture_output=True, text=True)
        assert r.returncode == 0
        assert "ZICE PASS" in r.stdout
        assert "33" in r.stdout or "30" in r.stdout

    def test_bushu_sh(self):
        lu = os.path.join(GEN, "jiaoben", "bushu.sh")
        assert os.path.exists(lu)
        r = subprocess.run(["bash", "-n", lu], capture_output=True)
        assert r.returncode == 0

    def test_peizhi_shi(self):
        lu = os.path.join(GEN, "ceshi", "test_quanju.py")
        assert os.path.exists(lu)