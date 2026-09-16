package main

import (
	"bufio"
	"bytes"
	"context"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"
)

type renwu struct {
	Bianhao  string `json:"bianhao"`
	Ming     string `json:"ming"`
	Canliang int    `json:"canliang"`
	ChangShi int    `json:"chang_shi"`
	Canshu   string `json:"canshu"`
}

type mingling_bao struct {
	Mingling string `json:"mingling"`
	LingPai  string `json:"ling_pai"`
	Renwu    renwu  `json:"renwu"`
	Bianhao  string `json:"bianhao"`
	LaiYuan  string `json:"laiyuan"`
}

type xin_xi_bao struct {
	FuZai    fu_zai_xin `json:"fuzai"`
	RenwuLie []renwu    `json:"renwu_lie"`
	WanLie   []string   `json:"wan_lie"`
}

type biaoge struct {
	sync.Mutex
	ziji         map[string]renwu
	wan_cun      map[string]int
	wan_xu       []string
	tade         map[string][]renwu
	tade_fuzai   map[string]fu_zai_xin
	ta_wan       map[string]map[string]bool
	jiedian      string
	shuju        string
	renwu_mulu   string
	bingfa       int
	canliang_s   uint64
	ling_pai     string
	renwu_duan   int
	cpu_yu       int
	mem_yu       int
	zi_fuzai     fu_zai_xin
	shangci_zong float64
	shangci_xian float64
	gengxin      func()
}

func xin_biaoge(jiedian, shuju string, bingfa int, canliang_s uint64, ling_pai string) *biaoge {
	if bingfa <= 0 {
		bingfa = 8
	}
	if canliang_s == 0 {
		canliang_s = 50000000
	}
	return &biaoge{
		ziji:       map[string]renwu{},
		wan_cun:    map[string]int{},
		tade:       map[string][]renwu{},
		tade_fuzai: map[string]fu_zai_xin{},
		jiedian:    jiedian,
		shuju:      shuju,
		renwu_mulu: "/opt/weixing/renwu",
		bingfa:     bingfa,
		canliang_s: canliang_s,
		ling_pai:   ling_pai,
		renwu_duan: 7947,
		cpu_yu:     85,
		mem_yu:     85,
	}
}

func (b *biaoge) liang_fuzai() fu_zai_xin {
	b.Lock()
	defer b.Unlock()
	b.zi_fuzai.RenwuShu = len(b.ziji)
	var lei int64
	for _, rr := range b.ziji {
		lei += int64(rr.Canliang)
	}
	b.zi_fuzai.LeiJi = lei
	zong, xian, hao := du_cpu()
	if hao {
		if b.shangci_zong > 0 && zong > b.shangci_zong {
			zhan := 100.0 * (zong - b.shangci_zong - (xian - b.shangci_xian)) / (zong - b.shangci_zong)
			if zhan < 0 {
				zhan = 0
			}
			if zhan > 100 {
				zhan = 100
			}
			b.zi_fuzai.Cpu = zhan
		}
		b.shangci_zong = zong
		b.shangci_xian = xian
	}
	b.zi_fuzai.Neicun = du_neicun()
	return b.zi_fuzai
}

func (b *biaoge) ziji_fuzai() (fu_zai_xin, bool) {
	fu := b.liang_fuzai()
	return fu, fu.Cpu < float64(b.cpu_yu) && fu.Neicun < b.mem_yu
}

func (b *biaoge) qu_fuzai(jiedian string) (fu_zai_xin, bool) {
	b.Lock()
	defer b.Unlock()
	fu, you := b.tade_fuzai[jiedian]
	return fu, you
}

func (b *biaoge) ta_fuzai_qu() map[string]fu_zai_xin {
	b.Lock()
	defer b.Unlock()
	chu := make(map[string]fu_zai_xin, len(b.tade_fuzai))
	for ming, fu := range b.tade_fuzai {
		chu[ming] = fu
	}
	return chu
}

func (b *biaoge) shan_tade(jiedian string) {
	b.Lock()
	delete(b.tade, jiedian)
	delete(b.tade_fuzai, jiedian)
	b.Unlock()
}

func yan_ling_pai(ben, shou string) bool {
	if ben == "" {
		return true
	}
	return subtle.ConstantTimeCompare([]byte(ben), []byte(shou)) == 1
}

func (b *biaoge) man_le() bool {
	b.Lock()
	defer b.Unlock()
	return len(b.ziji) >= b.bingfa
}

func (b *biaoge) cha(bianhao string) int {
	b.Lock()
	defer b.Unlock()
	if _, zai_pao := b.ziji[bianhao]; zai_pao {
		return 1
	}
	if _, yi_wan := b.wan_cun[bianhao]; yi_wan {
		return 2
	}
	return 0
}

func (b *biaoge) shou_meta(jiedian string, meta []byte) {
	if len(meta) == 0 || jiedian == b.jiedian {
		return
	}
	var bao xin_xi_bao
	if json.Unmarshal(meta, &bao) != nil {
		var liebiao []renwu
		if json.Unmarshal(meta, &liebiao) != nil {
			return
		}
		bao = xin_xi_bao{RenwuLie: liebiao}
	}
	b.Lock()
	b.tade[jiedian] = bao.RenwuLie
	b.tade_fuzai[jiedian] = bao.FuZai
	if b.ta_wan == nil {
		b.ta_wan = map[string]map[string]bool{}
	}
	ta_wan := map[string]bool{}
	for _, bh := range bao.WanLie {
		ta_wan[bh] = true
	}
	b.ta_wan[jiedian] = ta_wan
	b.Unlock()
}

func (b *biaoge) chu_meta(xian_zhi int) []byte {
	fu := b.liang_fuzai()
	b.Lock()
	liebiao := make([]renwu, 0, len(b.ziji))
	for _, r := range b.ziji {
		liebiao = append(liebiao, r)
	}
	wan_lie := make([]string, 0, 8)
	for i := len(b.wan_xu) - 1; i >= 0 && len(wan_lie) < 8; i-- {
		wan_lie = append(wan_lie, b.wan_xu[i])
	}
	b.Unlock()
	sort.Slice(liebiao, func(i, j int) bool { return liebiao[i].Bianhao < liebiao[j].Bianhao })
	if xian_zhi <= 0 || xian_zhi > 512 {
		xian_zhi = 512
	}
	bao := xin_xi_bao{FuZai: fu, RenwuLie: liebiao, WanLie: wan_lie}
	wei, _ := json.Marshal(bao)
	for len(wei) > xian_zhi && len(bao.RenwuLie) > 0 {
		bao.RenwuLie = bao.RenwuLie[:len(bao.RenwuLie)-1]
		wei, _ = json.Marshal(bao)
	}
	return wei
}

func (b *biaoge) jiaru(r renwu) int {
	if r.Canliang <= 0 {
		r.Canliang = 200000
	}
	if r.ChangShi <= 0 {
		r.ChangShi = 1
	}
	b.Lock()
	_, zai_pao := b.ziji[r.Bianhao]
	yi_cishi, yi_wan := b.wan_cun[r.Bianhao]
	ma_fang := yi_wan && r.ChangShi <= yi_cishi
	if !zai_pao && !ma_fang {
		b.ziji[r.Bianhao] = r
	}
	b.Unlock()
	if !zai_pao && !ma_fang && b.gengxin != nil {
		b.gengxin()
	}
	if ma_fang {
		return 2
	}
	if zai_pao {
		return 1
	}
	return 0
}

func (b *biaoge) wancheng(r renwu) {
	b.Lock()
	delete(b.ziji, r.Bianhao)
	if r.ChangShi <= 0 {
		r.ChangShi = 1
	}
	if _, you := b.wan_cun[r.Bianhao]; !you {
		b.wan_xu = append(b.wan_xu, r.Bianhao)
	}
	b.wan_cun[r.Bianhao] = r.ChangShi
	for len(b.wan_xu) > 64 {
		shan := b.wan_xu[0]
		b.wan_xu = b.wan_xu[1:]
		delete(b.wan_cun, shan)
	}
	b.Unlock()
	if b.gengxin != nil {
		b.gengxin()
	}
}

func (b *biaoge) fuwu(duan int) {
	l, cuo := net.Listen("tcp", fmt.Sprintf(":%d", duan))
	if cuo != nil {
		fmt.Println("renwu fuwu qidong shibai:", cuo)
		return
	}
	for {
		lian, cuo := l.Accept()
		if cuo != nil {
			continue
		}
		go b.chu_li(lian)
	}
}

func (b *biaoge) qian_zhi_canliang(r *renwu) {
	if r.Canliang < 0 || uint64(r.Canliang) > b.canliang_s {
		r.Canliang = int(b.canliang_s)
	}
}

func (b *biaoge) chu_li(lian net.Conn) {
	defer lian.Close()
	lian.SetDeadline(time.Now().Add(30 * time.Second))
	sao := bufio.NewScanner(lian)
	sao.Buffer(make([]byte, 4096), 65536)
	if !sao.Scan() {
		return
	}
	var bao mingling_bao
	if json.Unmarshal(sao.Bytes(), &bao) != nil {
		lian.Write([]byte("{\"jieguo\":\"HUAI\"}\n"))
		return
	}
	if !yan_ling_pai(b.ling_pai, bao.LingPai) {
		lian.Write([]byte("{\"jieguo\":\"JUJUE\"}\n"))
		return
	}
	switch bao.Mingling {
	case "PAIFA":
		if b.man_le() {
			lian.Write([]byte("{\"jieguo\":\"MAN\"}\n"))
			return
		}
		b.qian_zhi_canliang(&bao.Renwu)
		zhuang := map[int]string{0: "XIN", 1: "CHONGFU", 2: "YIWAN"}
		ma := b.jiaru(bao.Renwu)
		lian.Write([]byte("{\"jieguo\":\"OK\",\"zhuangtai\":\"" + zhuang[ma] + "\"}\n"))
		if ma == 0 {
			laiyuan := bao.LaiYuan
			if laiyuan == "" {
				laiyuan = "ZHIJIE"
			}
			go b.zhixing(bao.Renwu, laiyuan)
		}
	case "CHA":
		zhuang := map[int]string{0: "MEI_YOU", 1: "ZAI_PAO", 2: "YI_WAN"}
		lian.Write([]byte("{\"jieguo\":\"OK\",\"zhuangtai\":\"" + zhuang[b.cha(bao.Bianhao)] + "\"}\n"))
	default:
		lian.Write([]byte("{\"jieguo\":\"HUAI\"}\n"))
	}
}

func ming_an_quan(ming string) bool {
	if ming == "" || len(ming) > 64 {
		return false
	}
	return filepath.Base(ming) == ming && ming != "." && ming != ".."
}

func (b *biaoge) pao_zhen(r *renwu) (string, string, bool) {
	if !ming_an_quan(r.Ming) {
		return "", "", false
	}
	liu := filepath.Join(b.renwu_mulu, r.Ming)
	if st, cuo := os.Stat(liu); cuo != nil || st.IsDir() {
		return "", "", false
	}
	ctx, quxiao := context.WithTimeout(context.Background(), 120*time.Second)
	defer quxiao()
	cmd := exec.CommandContext(ctx, "/bin/sh", liu, r.Canshu)
	chu := &bytes.Buffer{}
	cmd.Stdout = chu
	cmd.Stderr = chu
	cuo := cmd.Run()
	shuchu := chu.String()
	if len(shuchu) > 256 {
		shuchu = shuchu[:256]
	}
	if cuo != nil {
		return "cuo_wu", shuchu, true
	}
	return "wan_bi", shuchu, true
}

func (b *biaoge) pao_xuni(r *renwu) string {
	ha := sha256.Sum256([]byte(r.Bianhao + ":" + r.Ming))
	for i := 0; i < r.Canliang; i++ {
		ha = sha256.Sum256(ha[:])
		if i&65535 == 65535 {
			runtime.Gosched()
		}
	}
	return hex.EncodeToString(ha[:8])
}

func (b *biaoge) zhixing(r renwu, laiyuan string) {
	kaishi := time.Now()
	jieguo, shuchu, zhen := b.pao_zhen(&r)
	if !zhen {
		jieguo = b.pao_xuni(&r)
	}
	haoshi := time.Since(kaishi).Milliseconds()
	g := map[string]interface{}{
		"renwu":      r.Bianhao,
		"ming":       r.Ming,
		"jiedian":    b.jiedian,
		"laiyuan":    laiyuan,
		"hao_shi_ms": haoshi,
		"jieguo":     jieguo,
		"shuchu":     shuchu,
		"wancheng":   time.Now().Format("15:04:05"),
	}
	b.xie_jieguo(g)
	fmt.Printf("[%s] RENWU_WANCHENG %s(%s) laiyuan=%s haoshi=%dms jieguo=%s\n",
		time.Now().Format("15:04:05"), r.Bianhao, r.Ming, laiyuan, haoshi, jieguo)
	b.wancheng(r)
}

func (b *biaoge) xie_jieguo(g map[string]interface{}) {
	if b.shuju == "" {
		return
	}
	os.MkdirAll(b.shuju, 0755)
	wei, _ := json.Marshal(g)
	lu := filepath.Join(b.shuju, "renwu_"+b.jiedian+".json")
	lun_zhuan_wen(lu)
	f, cuo := os.OpenFile(lu, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if cuo != nil {
		return
	}
	f.Write(append(wei, '\n'))
	f.Close()
}

func lun_zhuan_wen(lu string) {
	xin, cuo := os.Stat(lu)
	if cuo != nil || xin.Size() <= 1<<20 {
		return
	}
	f, cuo := os.OpenFile(lu, os.O_RDWR, 0644)
	if cuo != nil {
		return
	}
	defer f.Close()
	weiba := make([]byte, 65536)
	if xin.Size() < int64(len(weiba)) {
		weiba = make([]byte, xin.Size())
	}
	da, _ := f.ReadAt(weiba, xin.Size()-int64(len(weiba)))
	weiba = weiba[:da]
	if duan := bytes.LastIndexByte(weiba, '\n'); duan >= 0 {
		weiba = weiba[:duan+1]
	}
	if f.Truncate(0) == nil {
		f.WriteAt(weiba, 0)
	}
}

func (b *biaoge) qu_tawan(siming string) map[string]bool {
	b.Lock()
	defer b.Unlock()
	wan := b.ta_wan[siming]
	chu := map[string]bool{}
	for bh := range wan {
		chu[bh] = true
	}
	return chu
}

func (b *biaoge) qu_tade(siming string) []renwu {
	b.Lock()
	defer b.Unlock()
	return append([]renwu(nil), b.tade[siming]...)
}

func xuan_jie_mubiao(zi fu_zai_xin, zi_ke bool, ta map[string]fu_zai_xin, canliang_s uint64) string {
	zui := ""
	zui_zhi := 1e18
	for ming, fu := range ta {
		zhi := yu_ce_fen(fu, canliang_s)
		if zhi < zui_zhi || (zhi == zui_zhi && (zui == "" || ming < zui)) {
			zui_zhi = zhi
			zui = ming
		}
	}
	if !zi_ke {
		return zui
	}
	if zui == "" || yu_ce_fen(zi, canliang_s) <= zui_zhi {
		return ""
	}
	return zui
}

func (b *biaoge) fa_paifa(di_zhi string, r renwu, laiyuan string) bool {
	lian, cuo := net.DialTimeout("tcp", fmt.Sprintf("%s:%d", di_zhi, b.renwu_duan), 5*time.Second)
	if cuo != nil {
		return false
	}
	defer lian.Close()
	lian.SetDeadline(time.Now().Add(10 * time.Second))
	bao := mingling_bao{Mingling: "PAIFA", LingPai: b.ling_pai, Renwu: r, LaiYuan: laiyuan}
	wei, _ := json.Marshal(bao)
	if _, cuo = lian.Write(append(wei, '\n')); cuo != nil {
		return false
	}
	hui := make([]byte, 128)
	n, cuo := lian.Read(hui)
	if cuo != nil {
		return false
	}
	return strings.Contains(string(hui[:n]), "\"jieguo\":\"OK\"")
}
