package main

import (
	"encoding/json"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func du_zui_hou(mu, jiedian string) map[string]interface{} {
	nei, _ := os.ReadFile(filepath.Join(mu, "renwu_"+jiedian+".json"))
	hang := strings.Split(strings.TrimSpace(string(nei)), "\n")
	var g map[string]interface{}
	json.Unmarshal([]byte(hang[len(hang)-1]), &g)
	return g
}

func TestZhixingZhenShiRenWu(t *testing.T) {
	mu := t.TempDir()
	if cuo := os.WriteFile(filepath.Join(mu, "ceshi_js"), []byte("echo nihao $1\n"), 0755); cuo != nil {
		t.Fatal(cuo)
	}
	b := xin_biaoge("xingA", mu, 8, 50000000, "")
	b.renwu_mulu = mu
	b.zhixing(renwu{Bianhao: "rw-z", Ming: "ceshi_js", Canshu: "peng_you"}, "CESHI")
	g := du_zui_hou(mu, "xingA")
	if g["jieguo"] != "wan_bi" || !strings.Contains(g["shuchu"].(string), "nihao peng_you") {
		t.Fatalf("zhen shi renwu shibai: %v", g)
	}
}

func TestZhixingZhenShiCuoWu(t *testing.T) {
	mu := t.TempDir()
	if cuo := os.WriteFile(filepath.Join(mu, "cuo_js"), []byte("exit 3\n"), 0755); cuo != nil {
		t.Fatal(cuo)
	}
	b := xin_biaoge("xingA", mu, 8, 50000000, "")
	b.renwu_mulu = mu
	b.zhixing(renwu{Bianhao: "rw-c", Ming: "cuo_js"}, "CESHI")
	g := du_zui_hou(mu, "xingA")
	if g["jieguo"] != "cuo_wu" {
		t.Fatalf("fei ling tui chu ying ji cuo_wu: %v", g)
	}
}

func TestZhixingXuniHuiTui(t *testing.T) {
	mu := t.TempDir()
	b := xin_biaoge("xingA", mu, 8, 50000000, "")
	b.renwu_mulu = mu
	b.zhixing(renwu{Bianhao: "rw-x", Ming: "bu_cun_zai", Canliang: 100}, "CESHI")
	g := du_zui_hou(mu, "xingA")
	if len(g["jieguo"].(string)) != 16 {
		t.Fatalf("xuni hui tui shibai: %v", g)
	}
}

func TestMingLuJing(t *testing.T) {
	mu := t.TempDir()
	if cuo := os.WriteFile(filepath.Join(mu, "tao_can"), []byte("echo hai\n"), 0755); cuo != nil {
		t.Fatal(cuo)
	}
	b := xin_biaoge("xingA", mu, 8, 50000000, "")
	b.renwu_mulu = mu
	b.zhixing(renwu{Bianhao: "rw-p", Ming: "../tao_can", Canliang: 10}, "CESHI")
	g := du_zui_hou(mu, "xingA")
	if len(g["jieguo"].(string)) != 16 {
		t.Fatalf("lu jing chuan yue ying bei ju jue: %v", g)
	}
}

func TestCeYuanHuan(t *testing.T) {
	b := xin_biaoge("xingA", "", 8, 50000000, "")
	b.jiaru(renwu{Bianhao: "rw-1", Ming: "mubiao_shibie", Canliang: 100})
	meta := b.chu_meta(512)
	t.Log("meta:", string(meta))
	var bao xin_xi_bao
	if json.Unmarshal(meta, &bao) != nil {
		t.Fatalf("meta bu shi xin_xi_bao: %s", string(meta))
	}
	if bao.FuZai.RenwuShu != 1 || len(bao.RenwuLie) != 1 || bao.RenwuLie[0].Bianhao != "rw-1" {
		t.Fatalf("yuan huan shibai: %+v", bao)
	}
	c := xin_biaoge("xingB", "", 8, 50000000, "")
	c.shou_meta("xingA", meta)
	de := c.qu_tade("xingA")
	if len(de) != 1 || de[0].Bianhao != "rw-1" || de[0].Canliang != 100 {
		t.Fatalf("yuan huan shibai: %+v", de)
	}
	fu, you := c.qu_fuzai("xingA")
	if !you || fu.RenwuShu != 1 {
		t.Fatalf("fuzai yuan huan shibai: %+v %v", fu, you)
	}
}

func TestJiuGeShiMeta(t *testing.T) {
	c := xin_biaoge("xingB", "", 8, 50000000, "")
	c.shou_meta("xingA", []byte(`[{"bianhao":"rw-9","ming":"ceshi","canliang":50,"chang_shi":1}]`))
	de := c.qu_tade("xingA")
	if len(de) != 1 || de[0].Bianhao != "rw-9" {
		t.Fatalf("jiu ge shi ying jian rong: %+v", de)
	}
}

func TestMetaXianZhi(t *testing.T) {
	b := xin_biaoge("xingA", "", 8, 50000000, "")
	for i := 0; i < 6; i++ {
		b.jiaru(renwu{Bianhao: fmt.Sprintf("rw-%d", i), Ming: "yaogan_shaixuan", Canliang: 300000})
	}
	meta := b.chu_meta(120)
	if len(meta) > 120 {
		t.Fatalf("meta chao xian: %d", len(meta))
	}
	var bao xin_xi_bao
	if json.Unmarshal(meta, &bao) != nil {
		t.Fatalf("ya suo hou meta huai: %s", string(meta))
	}
	if len(bao.RenwuLie) >= 6 {
		t.Fatal("ying cai diao bu fen renwu")
	}
	if bao.FuZai.RenwuShu != 6 {
		t.Fatalf("renwu_shu ying wei zhen shi zhi 6: %+v", bao.FuZai)
	}
}

func TestXuanJieMubiao(t *testing.T) {
	if xuan_jie_mubiao(fu_zai_xin{Cpu: 10, Neicun: 10}, true, nil, 50000000) != "" {
		t.Fatal("wu lin ju ying ben di jie guan")
	}
	ta := map[string]fu_zai_xin{
		"xingB": {Cpu: 90, Neicun: 50},
		"xingC": {Cpu: 5, Neicun: 10},
	}
	if xuan_jie_mubiao(fu_zai_xin{Cpu: 90, Neicun: 90}, false, ta, 50000000) != "xingC" {
		t.Fatal("zi man ying zhuan pai zui xian de xingC")
	}
	if xuan_jie_mubiao(fu_zai_xin{Cpu: 20, Neicun: 10}, true, ta, 50000000) != "xingC" {
		t.Fatal("xingC geng xian ying zhuan pai")
	}
	if xuan_jie_mubiao(fu_zai_xin{Cpu: 3, Neicun: 5}, true, map[string]fu_zai_xin{"xingB": {Cpu: 80, Neicun: 90}}, 50000000) != "" {
		t.Fatal("zi geng xian ying ben di jie guan")
	}
	ping := map[string]fu_zai_xin{"xingC": {Cpu: 10, Neicun: 10}, "xingB": {Cpu: 10, Neicun: 10}}
	if xuan_jie_mubiao(fu_zai_xin{Cpu: 99, Neicun: 99}, false, ping, 50000000) != "xingB" {
		t.Fatal("ping ju ying an ming zi pai xu")
	}
}

func TestYuCeFen(t *testing.T) {
	xian := fu_zai_xin{Cpu: 10, Neicun: 10, LeiJi: 0}
	mang := fu_zai_xin{Cpu: 20, Neicun: 20, LeiJi: 50000000}
	if yu_ce_fen(mang, 50000000) <= yu_ce_fen(xian, 50000000) {
		t.Fatal("zai tu ren wu liang ying tui gao fen")
	}
	if yu_ce_fen(xian, 50000000) != 10.0 {
		t.Fatalf("wu bei fen bu dui: %v", yu_ce_fen(xian, 50000000))
	}
	man := fu_zai_xin{Cpu: 0, Neicun: 0, LeiJi: 999999999}
	if yu_ce_fen(man, 50000000) != 30.0 {
		t.Fatalf("bei fen ying feng ding: %v", yu_ce_fen(man, 50000000))
	}
	jie := map[string]float64{"xingB": 40.0, "xingC": 10.0}
	if tiao_zui_jia(jie) != "xingC" {
		t.Fatal("jing jia tiao xuan cuo wu")
	}
	if tiao_zui_jia(nil) != "" {
		t.Fatal("kong jing jia ying kong")
	}
}

func TestWanLieYuanHuan(t *testing.T) {
	b := xin_biaoge("xingA", "", 8, 50000000, "")
	b.jiaru(renwu{Bianhao: "rw-9", Ming: "ceshi", Canliang: 10})
	b.wancheng(renwu{Bianhao: "rw-9", Ming: "ceshi"})
	meta := b.chu_meta(512)
	c := xin_biaoge("xingB", "", 8, 50000000, "")
	c.shou_meta("xingA", meta)
	wan := c.qu_tawan("xingA")
	if !wan["rw-9"] {
		t.Fatalf("wan_lie ying han rw-9: %v", wan)
	}
	if len(meta) > 512 {
		t.Fatalf("meta chao xian: %d", len(meta))
	}
}

func TestLeiJi(t *testing.T) {
	b := xin_biaoge("xingA", "", 8, 50000000, "")
	b.jiaru(renwu{Bianhao: "rw-a", Canliang: 100000})
	b.jiaru(renwu{Bianhao: "rw-b", Canliang: 200000})
	fu := b.liang_fuzai()
	if fu.LeiJi != 300000 {
		t.Fatalf("leiji ying wei 300000: %d", fu.LeiJi)
	}
}

func TestLiangFuzai(t *testing.T) {
	b := xin_biaoge("xingA", "", 8, 50000000, "")
	fu := b.liang_fuzai()
	if fu.RenwuShu != 0 || fu.Neicun < 0 || fu.Neicun > 100 {
		t.Fatalf("shou ci liang liang chang: %+v", fu)
	}
	b.jiaru(renwu{Bianhao: "rw-1", Canliang: 10})
	fu = b.liang_fuzai()
	if fu.RenwuShu != 1 {
		t.Fatalf("renwu_shu ying wei 1: %+v", fu)
	}
	if fu.Cpu < 0 || fu.Cpu > 100 {
		t.Fatalf("cpu yue jie: %+v", fu)
	}
}

func TestFaPaifa(t *testing.T) {
	b := xin_biaoge("xingA", "", 8, 50000000, "")
	r := renwu{Bianhao: "rw-1", Ming: "ceshi", Canliang: 10}
	b.renwu_duan = 1
	if b.fa_paifa("127.0.0.1", r, "JIEGUAN") {
		t.Fatal("bu ke da duan kou ying shibai")
	}
	fu, cuo := net.Listen("tcp", "127.0.0.1:0")
	if cuo != nil {
		t.Skip("wu fa jian ting")
	}
	defer fu.Close()
	duankou := fu.Addr().(*net.TCPAddr).Port
	ci := 0
	go func() {
		for {
			lian, cuo := fu.Accept()
			if cuo != nil {
				return
			}
			buf := make([]byte, 4096)
			lian.Read(buf)
			ci++
			if ci == 1 {
				lian.Write([]byte("{\"jieguo\":\"OK\",\"zhuangtai\":\"XIN\"}\n"))
			} else {
				lian.Write([]byte("{\"jieguo\":\"MAN\"}\n"))
			}
			lian.Close()
		}
	}()
	b.renwu_duan = duankou
	if !b.fa_paifa("127.0.0.1", r, "JIEGUAN") {
		t.Fatal("zheng chang fu wu ying cheng gong")
	}
	if b.fa_paifa("127.0.0.1", renwu{Bianhao: "rw-2", Canliang: 1}, "JIEGUAN") {
		t.Fatal("MAN hui ying ying shibai")
	}
}

func TestJiaruQuChong(t *testing.T) {
	b := xin_biaoge("xingA", "", 8, 50000000, "")
	r := renwu{Bianhao: "rw-1", Ming: "ceshi", Canliang: 10, ChangShi: 1}
	if b.jiaru(r) != 0 {
		t.Fatal("xin renwu ying wei 0")
	}
	if b.jiaru(r) != 1 {
		t.Fatal("chongfu PAIFA ying wei 1(zai pao)")
	}
	b.wancheng(r)
	if b.jiaru(r) != 2 {
		t.Fatal("yi wancheng ying wei 2")
	}
	r2 := r
	r2.ChangShi = 2
	if b.jiaru(r2) != 0 {
		t.Fatal("geng gao chang shi ying chong pao")
	}
	for i := 0; i < 70; i++ {
		b.wancheng(renwu{Bianhao: fmt.Sprintf("rw-x%d", i), ChangShi: 1})
	}
	if len(b.wan_cun) > 64 {
		t.Fatal("wan_cun wei an 64 tui chu")
	}
}

func TestYanLingPai(t *testing.T) {
	if !yan_ling_pai("", "renhe") {
		t.Fatal("wei pei zhi mi yao shi ying fang xing")
	}
	if yan_ling_pai("mi", "cuo") {
		t.Fatal("cuo wu ling pai ying ju jue")
	}
	if !yan_ling_pai("mi", "mi") {
		t.Fatal("zheng que ling pai ying tong guo")
	}
}

func TestBingFaShangXian(t *testing.T) {
	b := xin_biaoge("xingA", "", 2, 50000000, "")
	if b.jiaru(renwu{Bianhao: "a", Canliang: 1}) != 0 {
		t.Fatal("a ying jie shou")
	}
	if b.jiaru(renwu{Bianhao: "b", Canliang: 1}) != 0 {
		t.Fatal("b ying jie shou")
	}
	if !b.man_le() {
		t.Fatal("bing fa 2 ying man")
	}
	if b.cha("a") != 1 || b.cha("b") != 1 || b.cha("c") != 0 {
		t.Fatal("cha zhuang tai cuo wu")
	}
}

func TestCanLiangQianZhi(t *testing.T) {
	b := xin_biaoge("xingA", "", 8, 1000, "")
	r := renwu{Bianhao: "big", Canliang: 99999999}
	b.qian_zhi_canliang(&r)
	if r.Canliang != 1000 {
		t.Fatal("canliang wei an shang xian qian zhi")
	}
}
