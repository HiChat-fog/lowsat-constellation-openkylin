package main

import (
	"encoding/json"
	"sort"
	"sync"
	"time"

	"github.com/hashicorp/memberlist"
)

type jing_jia_wen struct {
	Lai string  `json:"lai"`
	Hao uint64  `json:"hao"`
	Fen float64 `json:"fen"`
	Can int64   `json:"can"`
}

type jing_jia_hui struct {
	Lai string  `json:"lai"`
	Hao uint64  `json:"hao"`
	Fen float64 `json:"fen"`
	Shu int     `json:"shu"`
}

type jing_jia_bu struct {
	sync.Mutex
	xu  uint64
	dai map[uint64]chan jing_jia_hui
	lie *memberlist.Memberlist
	b   *biaoge
	shi time.Duration
}

func xin_jing_jia(lie *memberlist.Memberlist, b *biaoge) *jing_jia_bu {
	return &jing_jia_bu{dai: map[uint64]chan jing_jia_hui{}, lie: lie, b: b, shi: 2 * time.Second}
}

func (j *jing_jia_bu) shou_xiao_bao(bao []byte) {
	if len(bao) == 0 || bao[0] != '{' {
		return
	}
	var wen jing_jia_wen
	if err := json.Unmarshal(bao, &wen); err == nil && wen.Hao > 0 && wen.Lai != "" {
		if j.b != nil {
			fu := j.b.liang_fuzai()
			hui := jing_jia_hui{Lai: j.b.jiedian, Hao: wen.Hao,
				Fen: yu_ce_fen(fu, j.b.canliang_s) + 0.001*float64(fu.RenwuShu), Shu: fu.RenwuShu}
			if x := j.cheng_yuan(wen.Lai); x != nil {
				wei, _ := json.Marshal(hui)
				j.lie.SendBestEffort(x, wei)
			}
			return
		}
	}
	var hui jing_jia_hui
	if err := json.Unmarshal(bao, &hui); err == nil && hui.Hao > 0 && hui.Lai != "" {
		j.Lock()
		deng, you := j.dai[hui.Hao]
		j.Unlock()
		if you {
			select {
			case deng <- hui:
			default:
			}
		}
	}
}

func (j *jing_jia_bu) cheng_yuan(ming string) *memberlist.Node {
	if j.lie == nil {
		return nil
	}
	for _, x := range j.lie.Members() {
		if x.Name == ming && x.State == memberlist.StateAlive {
			return x
		}
	}
	return nil
}

func (j *jing_jia_bu) zheng_ji(huo []string) (map[string]float64, bool) {
	if len(huo) == 0 || j.lie == nil {
		return nil, false
	}
	j.Lock()
	j.xu++
	hao := j.xu
	deng := make(chan jing_jia_hui, len(huo))
	j.dai[hao] = deng
	j.Unlock()
	defer func() {
		j.Lock()
		delete(j.dai, hao)
		j.Unlock()
	}()
	wen := jing_jia_wen{Lai: j.b.jiedian, Hao: hao}
	wei, _ := json.Marshal(wen)
	fa_song := 0
	for _, ming := range huo {
		if x := j.cheng_yuan(ming); x != nil {
			if j.lie.SendBestEffort(x, wei) == nil {
				fa_song++
			}
		}
	}
	if fa_song == 0 {
		return nil, false
	}
	jie := map[string]float64{}
	jie_shu := time.Now().Add(j.shi)
	for time.Now().Before(jie_shu) && len(jie) < fa_song {
		select {
		case hui := <-deng:
			jie[hui.Lai] = hui.Fen
		case <-time.After(200 * time.Millisecond):
		}
	}
	return jie, len(jie) > 0
}

func tiao_zui_jia(jie map[string]float64) string {
	zui := ""
	zui_zhi := 1e18
	ming_lie := make([]string, 0, len(jie))
	for ming := range jie {
		ming_lie = append(ming_lie, ming)
	}
	sort.Strings(ming_lie)
	for _, ming := range ming_lie {
		if jie[ming] < zui_zhi {
			zui_zhi = jie[ming]
			zui = ming
		}
	}
	return zui
}

func (j *jing_jia_bu) jing_jia(huo []string, renwu_liebiao []renwu, zi fu_zai_xin, hui_kou func() string) string {
	if len(renwu_liebiao) == 0 {
		return ""
	}
	kuai_mubiao := hui_kou()
	if kuai_mubiao == "" && zi.RenwuShu < j.b.bingfa {
		return ""
	}
	jie, you := j.zheng_ji(huo)
	if you {
		m := tiao_zui_jia(jie)
		if m == j.b.jiedian {
			return ""
		}
		if m != "" {
			return m
		}
	}
	return kuai_mubiao
}
