import subprocess
import os
import shutil
import tempfile

import pytest

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOU_JIAO_CHA = shutil.which("riscv64-linux-gnu-gcc") is not None
YOU_LIBBPF = os.path.isdir("/tmp/openkylin-kernel/tools/lib/bpf")

class TestPeizhi:
    def test_peizhi_wenjian(self):
        lu = os.path.join(GEN, "peizhi", "weixing.conf")
        assert os.path.exists(lu)
        with open(lu) as f:
            nei = f.read()
        assert "jiedian=" in nei
        assert "zhoudao=" in nei
        assert "ku_lu=" in nei
        assert "cpu_yuzhi=" in nei

    def test_peizhi_gexing(self):
        lu = os.path.join(GEN, "agent", "peizhi.h")
        assert os.path.exists(lu)
        with open(lu) as f:
            s = f.read()
        assert "du_zhi" in s
        assert "/etc/weixing/weixing.conf" in s

    @pytest.mark.skipif(not (YOU_JIAO_CHA and YOU_LIBBPF), reason="que riscv64-gcc huo libbpf")
    def test_agent_bianyi(self):
        r = subprocess.run([
            "riscv64-linux-gnu-gcc", "-static", "-Wall", "-fsyntax-only",
            "-I" + os.path.join(GEN, "agent"),
            "-I/tmp/openkylin-kernel/tools/lib/bpf",
            os.path.join(GEN, "agent", "agent_yonghu.c"),
        ], capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[:2000])
        assert r.returncode == 0

    @pytest.mark.skipif(not YOU_JIAO_CHA, reason="que riscv64-gcc")
    def test_jiance_guanjian(self):
        r = subprocess.run([
            "riscv64-linux-gnu-gcc", "-static", "-Wall", "-fsyntax-only",
            "-I" + os.path.join(GEN, "gongju"),
            os.path.join(GEN, "gongju", "jiance.c"),
        ], capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[:2000])
        assert r.returncode == 0

    @pytest.mark.skipif(not YOU_JIAO_CHA, reason="que riscv64-gcc")
    def test_diaodu_guanjian(self):
        r = subprocess.run([
            "riscv64-linux-gnu-gcc", "-static", "-Wall", "-fsyntax-only",
            os.path.join(GEN, "gongju", "diaodu.c"),
        ], capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[:2000])
        assert r.returncode == 0

    def test_xingxin_go(self):
        lu = os.path.join(GEN, "xingxin", "main.go")
        assert os.path.exists(lu)
        with open(lu) as f:
            s = f.read()
        assert "du_peizhi" in s

    def test_shijian_liu_geshi(self):
        lu = os.path.join(GEN, "hetong", "shijian.schema.json")
        assert os.path.exists(lu)
        with open(lu) as f:
            import json
            p = json.load(f)
        for l in p["leixing"]:
            assert "ming" in l
            assert "shuoming" in l