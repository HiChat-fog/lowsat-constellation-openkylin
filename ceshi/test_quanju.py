import json
import sqlite3 as sq
import os
import socket
import sys
import threading
import time

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, "/tmp/qemu_env")
sys.path.insert(0, os.path.join(GEN, "mianban"))

import yunduan_mianban as mb
import diaodu_yun as dd


def xie_json(tmp_path, ming, neirong):
    lu = tmp_path / ming
    lu.write_text(json.dumps(neirong) + "\n")
    return str(lu)


class Jia_Fuwu:
    def __init__(self, hui=b'{"jieguo":"OK","zhuangtai":"XIN"}\n',
                 cha_hui=b'{"jieguo":"OK","zhuangtai":"ZAI_PAO"}\n'):
        self.hui = hui
        self.cha_hui = cha_hui
        self.fu = socket.socket()
        self.fu.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.fu.bind(("127.0.0.1", 0))
        self.fu.listen(5)
        self.duankou = self.fu.getsockname()[1]
        self.shoudao = []
        threading.Thread(target=self.pao, daemon=True).start()

    def pao(self):
        while True:
            try:
                lian, _ = self.fu.accept()
            except OSError:
                return
            with lian:
                shuju = lian.recv(4096).decode()
                self.shoudao.append(shuju)
                lian.sendall(self.cha_hui if '"CHA"' in shuju else self.hui)
                time.sleep(0.05)

class TestGuance:
    def test_zhengchang(self, tmp_path):
        mb.SHUJU = str(tmp_path)
        lu = xie_json(tmp_path, "weixing1.json",
                      {"shijian": "10:00:00", "jiedian": "weixing1", "cpu": 5.0,
                       "neicun": 10, "qiehuan": 100, "zong_sys": 500,
                       "sys_top": [], "suanli_top": [], "qiehuan_top": []})
        xin, xiugai = mb.du_xin("weixing1")
        assert xin is not None
        assert xin["jiedian"] == "weixing1"
        assert xiugai is not None

    def test_meiyou(self, tmp_path):
        mb.SHUJU = str(tmp_path)
        xin, xiugai = mb.du_xin("bukexing")
        assert xin is None
        assert xiugai is None

    def test_huansuan(self, tmp_path):
        mb.SHUJU = str(tmp_path)
        xin = {"jiedian": "weixing1", "cpu": 99.0, "neicun": 5}
        assert mb.zhuangtai_biaoji(xin, time.time()) == "告警"
        xin = {"jiedian": "weixing1", "cpu": 5.0, "neicun": 86}
        assert mb.zhuangtai_biaoji(xin, time.time()) == "告警"
        xin = {"jiedian": "weixing1", "cpu": 5.0, "neicun": 10}
        assert mb.zhuangtai_biaoji(xin, time.time()) == "正常"
        assert mb.zhuangtai_biaoji(None, time.time()) == "失联"
        assert mb.zhuangtai_biaoji(xin, time.time() - 20) == "失联"

    def test_shijianwenjian(self, tmp_path):
        mb.SHUJU = str(tmp_path)
        lu = tmp_path / "weixing2.shijian"
        lu.write_text("XITONG|weixing2|qidong\nALARM|weixing2|syscall 激增\n")
        assert mb.du_shijian_file("weixing2") == "ALARM|weixing2|syscall 激增"
        assert mb.jingbao("weixing2") == "ALARM|weixing2|syscall 激增"

    def test_du_xin_jiedian_ku(self, tmp_path):
        mb.SHUJU = str(tmp_path)
        k = sq.connect(str(tmp_path / "weixing3.db"))
        k.execute("CREATE TABLE guance(id INTEGER PRIMARY KEY AUTOINCREMENT, jiedian TEXT,"
                  "cpu REAL, neicun INTEGER, qiehuan INTEGER, zong_sys INTEGER, duc TEXT,"
                  "shijian DEFAULT (datetime('now','localtime')))")
        duc = json.dumps({"shijian": "10:00:00", "jiedian": "weixing3", "cpu": 7.0,
                          "neicun": 12, "qiehuan": 60, "zong_sys": 800})
        k.execute("INSERT INTO guance(jiedian,cpu,neicun,qiehuan,zong_sys,duc) VALUES(?,?,?,?,?,?)",
                  ("weixing3", 7.0, 12, 60, 800, duc))
        k.commit()
        k.close()
        xin, xiugai = mb.du_xin("weixing3")
        assert xin is not None
        assert xin["cpu"] == 7.0
        assert xiugai is not None

class TestDiaodu:
    def qian_zhi(self, tmp_path):
        dd.SHUJU = str(tmp_path)
        dd.MUBIAO.clear()
        dd.XUHAO = 0

    def test_fuzai(self, tmp_path):
        self.qian_zhi(tmp_path)
        xie_json(tmp_path, "weixing1.json",
                 {"shijian": "10:00:00", "jiedian": "weixing1", "cpu": 50.0, "neicun": 20, "qiehuan": 400})
        fuzai, xiugai = dd.du_fuzai("weixing1")
        assert fuzai is not None
        assert fuzai > 0
        assert xiugai is not None

    def test_fuzai_que(self, tmp_path):
        self.qian_zhi(tmp_path)
        xie_json(tmp_path, "weixing1.json", {"jiedian": "weixing1"})
        fuzai, xiugai = dd.du_fuzai("weixing1")
        assert fuzai is None

    def test_fuzai_yong_zeng(self, tmp_path):
        self.qian_zhi(tmp_path)
        xie_json(tmp_path, "weixing1.json",
                 {"shijian": "10:00:00", "jiedian": "weixing1", "cpu": 5.0, "neicun": 10,
                  "qiehuan": 90000, "qiehuan_zeng": 50})
        xie_json(tmp_path, "weixing2.json",
                 {"shijian": "10:00:00", "jiedian": "weixing2", "cpu": 5.0, "neicun": 10,
                  "qiehuan": 100, "qiehuan_zeng": 5000})
        fuzai1, _ = dd.du_fuzai("weixing1")
        fuzai2, _ = dd.du_fuzai("weixing2")
        assert fuzai1 < fuzai2
        ming, _ = dd.zui_xian()
        assert ming == "weixing1"

    def test_dai_fa_jian_xu(self, tmp_path):
        self.qian_zhi(tmp_path)
        fu = Jia_Fuwu()
        dd.DUANKOU = {"weixing1": fu.duankou, "weixing2": 59999, "weixing3": 59998}
        xie_json(tmp_path, "weixing1.json",
                 {"shijian": "10:00:00", "jiedian": "weixing1", "cpu": 5.0, "neicun": 10,
                  "qiehuan": 100, "qiehuan_zeng": 10})
        dd.MUBIAO.append({"renwu": {"bianhao": "rw-chang", "ming": "ceshi", "canliang": 500000,
                                    "chang_shi": 1}, "mubiao": None, "huan": time.time(), "chu": time.time()})
        dd.MUBIAO.append({"renwu": {"bianhao": "rw-duan", "ming": "ceshi", "canliang": 100000,
                                    "chang_shi": 1}, "mubiao": None, "huan": time.time(), "chu": time.time()})
        dd.jiancha_yi()
        assert len(fu.shoudao) == 2
        assert json.loads(fu.shoudao[0])["renwu"]["bianhao"] == "rw-duan"
        assert json.loads(fu.shoudao[1])["renwu"]["bianhao"] == "rw-chang"
        assert len(dd.MUBIAO) == 2
        assert all(r["mubiao"] == "weixing1" and r["renwu"]["chang_shi"] == 2 for r in dd.MUBIAO)

    def test_shi_bai_bi_kai(self, tmp_path):
        self.qian_zhi(tmp_path)
        xie_json(tmp_path, "weixing2.json",
                 {"shijian": "10:00:00", "jiedian": "weixing2", "cpu": 1.0, "neicun": 5, "qiehuan": 10})
        dd.SHI_BAI["weixing2"] = time.time()
        ming, _ = dd.zui_xian()
        assert ming is None
        dd.SHI_BAI.clear()
        ming, _ = dd.zui_xian()
        assert ming == "weixing2"

    def test_zui_xian_paichu(self, tmp_path):
        self.qian_zhi(tmp_path)
        xie_json(tmp_path, "weixing1.json",
                 {"shijian": "10:00:00", "jiedian": "weixing1", "cpu": 80.0, "neicun": 30, "qiehuan": 800})
        xie_json(tmp_path, "weixing2.json",
                 {"shijian": "10:00:00", "jiedian": "weixing2", "cpu": 10.0, "neicun": 10, "qiehuan": 100})
        xie_json(tmp_path, "weixing3.json",
                 {"shijian": "10:00:00", "jiedian": "weixing3", "cpu": 40.0, "neicun": 20, "qiehuan": 400})
        ming, _ = dd.zui_xian()
        assert ming == "weixing2"
        ming, _ = dd.zui_xian(paichu=("weixing2",))
        assert ming == "weixing3"

    def test_paifa_chenggong(self, tmp_path):
        self.qian_zhi(tmp_path)
        fu = Jia_Fuwu()
        dd.DUANKOU = {"weixing1": fu.duankou, "weixing2": 59999, "weixing3": 59998}
        xie_json(tmp_path, "weixing1.json",
                 {"shijian": "10:00:00", "jiedian": "weixing1", "cpu": 30.0, "neicun": 15, "qiehuan": 300})
        dd.paifa()
        assert len(dd.MUBIAO) == 1
        assert dd.MUBIAO[0]["mubiao"] == "weixing1"
        time.sleep(0.2)
        assert len(fu.shoudao) == 1
        assert "PAIFA" in fu.shoudao[0]
        assert dd.MUBIAO[0]["renwu"]["bianhao"] in fu.shoudao[0]
        assert '"chang_shi": 1' in fu.shoudao[0] or '"chang_shi":1' in fu.shoudao[0]

    def test_yiwan_xiaozhang(self, tmp_path):
        self.qian_zhi(tmp_path)
        fu1 = Jia_Fuwu()
        dd.DUANKOU = {"weixing1": fu1.duankou, "weixing2": 59999, "weixing3": 59998}
        xie_json(tmp_path, "weixing1.json",
                 {"shijian": "10:00:00", "jiedian": "weixing1", "cpu": 30.0, "neicun": 15, "qiehuan": 300})
        dd.paifa()
        assert len(dd.MUBIAO) == 1
        lu1 = tmp_path / "weixing1.json"
        guo = os.stat(lu1)
        os.utime(lu1, (guo.st_atime - 60, guo.st_mtime - 60))
        fu2 = Jia_Fuwu(hui=b'{"jieguo":"OK","zhuangtai":"YIWAN"}\n',
                       cha_hui=b'{"jieguo":"OK","zhuangtai":"MEI_YOU"}\n')
        dd.DUANKOU["weixing2"] = fu2.duankou
        xie_json(tmp_path, "weixing2.json",
                 {"shijian": "10:00:10", "jiedian": "weixing2", "cpu": 20.0, "neicun": 10, "qiehuan": 200})
        dd.jiancha_yi()
        assert len(dd.MUBIAO) == 0

    def test_cha_xiaozhang(self, tmp_path):
        self.qian_zhi(tmp_path)
        fu1 = Jia_Fuwu()
        dd.DUANKOU = {"weixing1": fu1.duankou, "weixing2": 59999, "weixing3": 59998}
        xie_json(tmp_path, "weixing1.json",
                 {"shijian": "10:00:00", "jiedian": "weixing1", "cpu": 30.0, "neicun": 15, "qiehuan": 300})
        dd.paifa()
        assert len(dd.MUBIAO) == 1
        lu1 = tmp_path / "weixing1.json"
        guo = os.stat(lu1)
        os.utime(lu1, (guo.st_atime - 60, guo.st_mtime - 60))
        fu2 = Jia_Fuwu(cha_hui=b'{"jieguo":"OK","zhuangtai":"YI_WAN"}\n')
        dd.DUANKOU["weixing2"] = fu2.duankou
        xie_json(tmp_path, "weixing2.json",
                 {"shijian": "10:00:10", "jiedian": "weixing2", "cpu": 20.0, "neicun": 10, "qiehuan": 200})
        dd.jiancha_yi()
        assert len(dd.MUBIAO) == 0
        assert not any("PAIFA" in s for s in fu2.shoudao)

    def test_paifa_wu_jiedian(self, tmp_path):
        self.qian_zhi(tmp_path)
        dd.DUANKOU = {"weixing1": 59997, "weixing2": 59996, "weixing3": 59995}
        dd.paifa()
        assert len(dd.MUBIAO) == 1
        assert dd.MUBIAO[0]["mubiao"] is None

    def test_celue_fcfs(self, tmp_path):
        self.qian_zhi(tmp_path)
        dd.MUBIAO.append({"renwu": {"bianhao": "rw-a", "canliang": 500000},
                          "mubiao": None, "huan": 0, "chu": 0})
        dd.MUBIAO.append({"renwu": {"bianhao": "rw-b", "canliang": 200000},
                          "mubiao": None, "huan": 0, "chu": 0})
        dd.CELUE = "FCFS"
        assert dd.dai_pai_lie()[0]["renwu"]["bianhao"] == "rw-a"
        dd.CELUE = "SJF"
        assert dd.dai_pai_lie()[0]["renwu"]["bianhao"] == "rw-b"
        dd.CELUE = "SJF"

    def test_man_bu_lengque(self, tmp_path):
        self.qian_zhi(tmp_path)
        fu = Jia_Fuwu(hui=b'{"jieguo":"MAN"}\n')
        dd.DUANKOU = {"weixing1": fu.duankou, "weixing2": 59999, "weixing3": 59998}
        renwu = {"bianhao": "rw-1", "canliang": 100000, "chang_shi": 1}
        hao, zhuang = dd.song_renwu("weixing1", renwu)
        assert not hao and zhuang == "MAN"
        assert "weixing1" not in dd.SHI_BAI

    def test_daifa_chong_shi(self, tmp_path):
        self.qian_zhi(tmp_path)
        dd.DUANKOU = {"weixing1": 59997, "weixing2": 59996, "weixing3": 59995}
        dd.paifa()
        assert dd.MUBIAO[0]["mubiao"] is None
        fu = Jia_Fuwu()
        dd.DUANKOU["weixing2"] = fu.duankou
        xie_json(tmp_path, "weixing2.json",
                 {"shijian": "10:00:10", "jiedian": "weixing2", "cpu": 20.0, "neicun": 10, "qiehuan": 200})
        dd.jiancha_yi()
        assert len(dd.MUBIAO) == 1
        assert dd.MUBIAO[0]["mubiao"] == "weixing2"
        assert dd.MUBIAO[0]["renwu"]["chang_shi"] == 2

    def test_duizhang(self, tmp_path):
        self.qian_zhi(tmp_path)
        fu_zai = Jia_Fuwu(cha_hui=b'{"jieguo":"OK","zhuangtai":"ZAI_PAO"}\n')
        fu_wan = Jia_Fuwu(cha_hui=b'{"jieguo":"OK","zhuangtai":"YI_WAN"}\n')
        dd.DUANKOU = {"weixing1": fu_zai.duankou, "weixing2": fu_wan.duankou, "weixing3": 59995}
        dd.MUBIAO.append({"renwu": {"bianhao": "rw-1", "chang_shi": 1}, "mubiao": "weixing1",
                          "huan": time.time(), "chu": time.time()})
        dd.MUBIAO.append({"renwu": {"bianhao": "rw-2", "chang_shi": 1}, "mubiao": "weixing2",
                          "huan": time.time(), "chu": time.time()})
        dd.dui_zhang()
        bian = [r["renwu"]["bianhao"] for r in dd.MUBIAO]
        assert "rw-1" in bian
        assert "rw-2" not in bian

    def test_taizhang_huifu(self, tmp_path):
        self.qian_zhi(tmp_path)
        dd.XUHAO = 5
        dd.MUBIAO.append({"renwu": {"bianhao": "rw-5", "chang_shi": 2}, "mubiao": "weixing1",
                          "huan": time.time(), "chu": time.time()})
        dd.xie_taizhang()
        dd.XUHAO = 0
        dd.MUBIAO.clear()
        assert dd.du_taizhang()
        assert dd.XUHAO == 5
        assert dd.MUBIAO[0]["renwu"]["bianhao"] == "rw-5"

    def test_du_jieguo(self, tmp_path):
        self.qian_zhi(tmp_path)
        fu = Jia_Fuwu()
        dd.DUANKOU = {"weixing1": fu.duankou, "weixing2": 59999, "weixing3": 59998}
        xie_json(tmp_path, "weixing1.json",
                 {"shijian": "10:00:00", "jiedian": "weixing1", "cpu": 30.0, "neicun": 15, "qiehuan": 300})
        dd.paifa()
        bh = dd.MUBIAO[0]["renwu"]["bianhao"]
        (tmp_path / "renwu_weixing1.json").write_text(
            json.dumps({"renwu": bh, "ming": "yaogan_shaixuan", "jiedian": "weixing1",
                        "laiyuan": "ZHIJIE", "hao_shi_ms": 15, "jieguo": "ab12", "wancheng": "10:00:05"}) + "\n")
        dd.du_jieguo()
        assert len(dd.MUBIAO) == 0

    def test_du_jieguo_jieguan(self, tmp_path):
        self.qian_zhi(tmp_path)
        fu = Jia_Fuwu()
        dd.DUANKOU = {"weixing1": fu.duankou, "weixing2": 59999, "weixing3": 59998}
        xie_json(tmp_path, "weixing1.json",
                 {"shijian": "10:00:00", "jiedian": "weixing1", "cpu": 30.0, "neicun": 15, "qiehuan": 300})
        dd.paifa()
        bh = dd.MUBIAO[0]["renwu"]["bianhao"]
        (tmp_path / "renwu_weixing2.json").write_text(
            json.dumps({"renwu": bh, "ming": "mubiao_shibie", "jiedian": "weixing2",
                        "laiyuan": "JIEGUAN", "hao_shi_ms": 20, "jieguo": "cd34", "wancheng": "10:00:08"}) + "\n")
        dd.du_jieguo()
        assert len(dd.MUBIAO) == 0

    def test_qianyi_shiqu(self, tmp_path):
        self.qian_zhi(tmp_path)
        fu1 = Jia_Fuwu()
        dd.DUANKOU = {"weixing1": fu1.duankou, "weixing2": 59999, "weixing3": 59998}
        xie_json(tmp_path, "weixing1.json",
                 {"shijian": "10:00:00", "jiedian": "weixing1", "cpu": 30.0, "neicun": 15, "qiehuan": 300})
        dd.paifa()
        assert dd.MUBIAO[0]["mubiao"] == "weixing1"
        lu1 = tmp_path / "weixing1.json"
        guo = os.stat(lu1)
        os.utime(lu1, (guo.st_atime - 60, guo.st_mtime - 60))
        fu2 = Jia_Fuwu(cha_hui=b'{"jieguo":"OK","zhuangtai":"MEI_YOU"}\n')
        dd.DUANKOU["weixing2"] = fu2.duankou
        xie_json(tmp_path, "weixing2.json",
                 {"shijian": "10:00:10", "jiedian": "weixing2", "cpu": 20.0, "neicun": 10, "qiehuan": 200})
        dd.jiancha_yi()
        assert len(dd.MUBIAO) == 1
        assert dd.MUBIAO[0]["mubiao"] == "weixing2"
        assert dd.MUBIAO[0]["renwu"]["chang_shi"] == 2
        time.sleep(0.2)
        assert any("PAIFA" in s for s in fu2.shoudao)

class TestHetong:
    def test_schema_hefa(self):
        lu = os.path.join(GEN, "hetong", "guance.schema.json")
        with open(lu) as f:
            p = json.load(f)
        assert p["mingcheng"] == "guance-shuju"
        ziduan = {z["ming"] for z in p["zi_duan"]}
        assert {"shijian", "lunci", "jiedian", "cpu", "neicun", "qiehuan",
                "zhixing", "fanzhi", "zong_sys", "sys_top", "suanli_top", "qiehuan_top"} <= ziduan

    def test_agent_shuchu_fuhe_schema(self):
        lu = os.path.join(GEN, "hetong", "guance.schema.json")
        with open(lu) as f:
            p = json.load(f)
        ziduan = {z["ming"] for z in p["zi_duan"]}
        li = p["li"]
        assert set(li.keys()) <= ziduan
        assert isinstance(li["cpu"], (int, float))
        assert isinstance(li["zong_sys"], int)

    def test_shijian_geshi(self):
        lu = os.path.join(GEN, "hetong", "shijian.schema.json")
        with open(lu) as f:
            p = json.load(f)
        leixing = {l["ming"] for l in p["leixing"]}
        assert {"ALARM", "RECOVER", "XITONG", "ZIJIAN"} == leixing

    def test_sqlite_jiegou(self):
        lu = os.path.join(GEN, "hetong", "sqlite-jiegou.json")
        with open(lu) as f:
            p = json.load(f)
        biao = {b["ming"] for b in p["biao"]}
        assert {"guance", "shijian_biao"} == biao

class TestZhibiao:
    def ce_li(self, tmp_path, ri_hang, jieguo_lie):
        import zhibiao_baogao as zb
        return zb.ji_suan(ri_hang, jieguo_lie)

    def test_jichu(self, tmp_path):
        bao = self.ce_li(tmp_path, [
            "10:00:00|状态|weixing1:12.0|在途任务0|待发0",
            "10:00:03|派发|rw-1|weixing1|yaogan_shaixuan|负载21.0",
            "10:00:06|派发|rw-2|weixing2|yaogan_shaixuan|负载21.0",
        ], [
            {"renwu": "rw-1", "ming": "yaogan_shaixuan", "jiedian": "weixing1",
             "laiyuan": "ZHIJIE", "hao_shi_ms": 20, "jieguo": "ab", "wancheng": "10:00:09"},
            {"renwu": "rw-2", "ming": "yaogan_shaixuan", "jiedian": "weixing1",
             "laiyuan": "JIEGUAN", "hao_shi_ms": 30, "jieguo": "cd", "wancheng": "10:00:20"},
        ])
        assert bao["pai_fa_shu"] == 2
        assert bao["wan_cheng_shu"] == 2
        assert bao["zhi_da_shu"] == 1
        assert bao["jie_guan_shu"] == 1
        assert bao["quan_cheng_miao"]["p50"] == 6.0

    def test_jieguan_dabiao(self, tmp_path):
        bao = self.ce_li(tmp_path, [
            "10:00:00|派发|rw-1|weixing2|ceshi|负载1.0",
            "14:00:00|星间接管完成|rw-1|执行节点weixing1|执行88ms|云端观测全程17.9秒(要求<=60)",
            "15:00:00|星间接管完成|rw-9|执行节点weixing3|执行88ms|云端观测全程75.0秒(要求<=60)",
            "16:00:00|云端迁移|rw-5|离开weixing2|重派weixing3|中断8.0秒",
            "17:00:00|入列|rw-6|暂无可用节点,台账挂起待发",
            "18:00:00|销账|rw-6|已在weixing3完成,不再重派",
        ], [])
        hf = bao["jie_guan_hui_fu_miao"]
        assert hf["da_biao_60s_lv"] == 50.0
        assert hf["zui_da"] == 75.0
        assert bao["yun_duan_qian_yi_shu"] == 1
        assert bao["ru_lie_dai_fa_shu"] == 1
        assert bao["xiao_zhang_shu"] == 1

    def test_kua_tian(self, tmp_path):
        bao = self.ce_li(tmp_path, [
            "23:59:50|派发|rw-1|weixing1|ceshi|负载1.0",
        ], [
            {"renwu": "rw-1", "jiedian": "weixing1", "laiyuan": "ZHIJIE",
             "hao_shi_ms": 5, "wancheng": "00:00:10"},
        ])
        assert bao["quan_cheng_miao"]["p50"] == 20.0

    def test_wei_shu(self, tmp_path):
        import zhibiao_baogao as zb
        assert zb.wei_shu([], 50) is None
        assert zb.wei_shu([3, 1, 2], 50) == 2
        assert zb.wei_shu(list(range(1, 101)), 95) == 95
