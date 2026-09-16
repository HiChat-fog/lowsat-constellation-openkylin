package main

import (
	"crypto/sha256"
	"fmt"
	"os"
	"os/signal"
	"runtime/debug"
	"sort"
	"strconv"
	"syscall"
	"time"

	"github.com/hashicorp/memberlist"
)

type jiankong struct {
	liebiao *memberlist.Memberlist
	b       *biaoge
	jing    *jing_jia_bu
}

func (j *jiankong) NotifyJoin(xing *memberlist.Node) {
	fmt.Printf("[%s] 新节点加入: %s (%s)\n", time.Now().Format("15:04:05"), xing.Name, xing.Addr)
	j.b.shou_meta(xing.Name, xing.Meta)
}
func (j *jiankong) NotifyLeave(xing *memberlist.Node) {
	shike := time.Now()
	fmt.Printf("[%s] 节点离开: %s -> 星间自治接管其任务\n", shike.Format("15:04:05"), xing.Name)
	renwu_liebiao := j.b.qu_tade(xing.Name)
	wan_biao := j.b.qu_tawan(xing.Name)
	si_fu, si_fu_you := j.b.qu_fuzai(xing.Name)
	j.b.shan_tade(xing.Name)
	go j.jieguan(xing.Name, shike, renwu_liebiao, wan_biao, si_fu, si_fu_you)
}
func (j *jiankong) NotifyUpdate(xing *memberlist.Node) {
	j.b.shou_meta(xing.Name, xing.Meta)
}

func (j *jiankong) NodeMeta(limit int) []byte {
	return j.b.chu_meta(limit)
}
func (j *jiankong) NotifyMsg(bao []byte) {
	j.jing.shou_xiao_bao(bao)
}
func (j *jiankong) GetBroadcasts(int, int) [][]byte {
	return nil
}
func (j *jiankong) LocalState(bool) []byte        { return nil }
func (j *jiankong) MergeRemoteState([]byte, bool) {}

func (j *jiankong) jie_di_zhi(ming string) string {
	for _, x := range j.liebiao.Members() {
		if x.Name == ming {
			return fmt.Sprintf("%s:%d", x.Addr, j.b.renwu_duan)
		}
	}
	return ""
}

func (j *jiankong) jieguan(siming string, likai time.Time, renwu_liebiao []renwu, wan_biao map[string]bool, si_fu fu_zai_xin, si_fu_you bool) {
	huo := []string{}
	for _, x := range j.liebiao.Members() {
		if x.State == memberlist.StateAlive && x.Name != siming {
			huo = append(huo, x.Name)
		}
	}
	if len(huo) == 0 {
		fmt.Printf("[%s] 无存活节点可接管 %s 的任务\n", time.Now().Format("15:04:05"), siming)
		return
	}
	sort.Strings(huo)
	if huo[0] != j.b.jiedian {
		return
	}
	if len(renwu_liebiao) == 0 {
		return
	}
	if si_fu_you && si_fu.RenwuShu > len(renwu_liebiao) {
		fmt.Printf("[%s] 注意: %s 在跑任务 %d 个,meta仅存 %d 个,超出部分无法接管\n",
			time.Now().Format("15:04:05"), siming, si_fu.RenwuShu, len(renwu_liebiao))
	}
	zi_fu, zi_ke := j.b.ziji_fuzai()
	mubiao := j.jing.jing_jia(huo, renwu_liebiao, zi_fu, func() string {
		return xuan_jie_mubiao(zi_fu, zi_ke, j.b.ta_fuzai_qu(), j.b.canliang_s)
	})
	if mubiao == "" {
		fmt.Printf("[%s] 本节点(%s)接管 %s 的 %d 个任务: %v\n",
			time.Now().Format("15:04:05"), j.b.jiedian, siming, len(renwu_liebiao), ming_dan(renwu_liebiao))
		for _, r := range renwu_liebiao {
			if wan_biao[r.Bianhao] {
				fmt.Printf("[%s] 跳过 %s, 死者已完成过\n", time.Now().Format("15:04:05"), r.Bianhao)
				continue
			}
			if ma := j.b.jiaru(r); ma != 0 {
				fmt.Printf("[%s] 跳过 %s, zhuangtai=%d\n", time.Now().Format("15:04:05"), r.Bianhao, ma)
				continue
			}
			go func(r renwu) {
				j.b.zhixing(r, "JIEGUAN")
				fmt.Printf("[%s] 接管完成 %s 恢复用时 %d 毫秒(要求<=60000)\n",
					time.Now().Format("15:04:05"), r.Bianhao, time.Since(likai).Milliseconds())
			}(r)
		}
		return
	}
	di_zhi := j.jie_di_zhi(mubiao)
	fmt.Printf("[%s] 本节点(%s)接管 %s 的 %d 个任务,按负载转派 %s(%s): %v\n",
		time.Now().Format("15:04:05"), j.b.jiedian, siming, len(renwu_liebiao), mubiao, di_zhi, ming_dan(renwu_liebiao))
	for _, r := range renwu_liebiao {
		go func(r renwu) {
			if di_zhi != "" && j.b.fa_paifa(di_zhi, r, "JIEGUAN") {
				fmt.Printf("[%s] 已转派 %s -> %s 恢复用时 %d 毫秒(要求<=60000)\n",
					time.Now().Format("15:04:05"), r.Bianhao, mubiao, time.Since(likai).Milliseconds())
				return
			}
			j.b.zhixing(r, "JIEGUAN")
			fmt.Printf("[%s] 接管完成 %s 恢复用时 %d 毫秒(要求<=60000)\n",
				time.Now().Format("15:04:05"), r.Bianhao, time.Since(likai).Milliseconds())
		}(r)
	}
}

func ming_dan(liebiao []renwu) []string {
	ming := make([]string, 0, len(liebiao))
	for _, r := range liebiao {
		ming = append(ming, r.Bianhao)
	}
	return ming
}

func main() {
	ming := du_peizhi("jiedian")
	if ming == "" {
		ming = "weixing1"
	}
	if len(os.Args) > 1 {
		ming = os.Args[1]
	}
	duan := 7946
	if zhi := du_peizhi("duan"); zhi != "" {
		fmt.Sscanf(zhi, "%d", &duan)
	}
	if len(os.Args) > 2 {
		fmt.Sscanf(os.Args[2], "%d", &duan)
	}
	renwu_duan := 7947
	if zhi := du_peizhi("renwu_duan"); zhi != "" {
		fmt.Sscanf(zhi, "%d", &renwu_duan)
	}
	if len(os.Args) > 5 {
		fmt.Sscanf(os.Args[5], "%d", &renwu_duan)
	}
	shuju := du_peizhi("renwu_shuju")
	if shuju == "" {
		shuju = "/mnt/share/shuju"
	}
	if v := os.Getenv("WX_SHUJU"); v != "" {
		shuju = v
	}
	guangbo := du_peizhi("ip")
	if len(os.Args) > 3 {
		guangbo = os.Args[3]
	}
	lianjie := du_peizhi("la")
	if len(os.Args) > 4 {
		lianjie = os.Args[4]
	}
	bingfa := 8
	if zhi := du_peizhi("renwu_bingfa"); zhi != "" {
		fmt.Sscanf(zhi, "%d", &bingfa)
	}
	if v := os.Getenv("WX_RENWU_BINGFA"); v != "" {
		if shu, cuo := strconv.Atoi(v); cuo == nil && shu > 0 {
			bingfa = shu
		}
	}
	canliang_s := uint64(50000000)
	if zhi := du_peizhi("canliang_shang_xian"); zhi != "" {
		if zhi_shu, cuo := strconv.ParseUint(zhi, 10, 64); cuo == nil {
			canliang_s = zhi_shu
		}
	}
	ling_pai := du_peizhi("ling_pai")
	if v := os.Getenv("WX_LING_PAI"); v != "" {
		ling_pai = v
	}
	if ling_pai != "" {
		fmt.Printf("任务端口鉴权已开启\n")
	} else {
		fmt.Printf("JING_GAO: renwu_duan wei pei zhi ling_pai, ren he lai yuan jun ke PAIFA\n")
	}
	ban_ben := "dev"
	if xinxi, hao := debug.ReadBuildInfo(); hao {
		for _, she := range xinxi.Settings {
			if she.Key == "vcs.revision" && len(she.Value) >= 7 {
				ban_ben = she.Value[:7]
			}
			if she.Key == "vcs.modified" && she.Value == "true" {
				ban_ben += "-gai"
			}
		}
	}
	fmt.Printf("xingxin ban_ben=%s\n", ban_ben)

	jian := &jiankong{b: xin_biaoge(ming, shuju, bingfa, canliang_s, ling_pai)}
	jian.b.renwu_duan = renwu_duan
	if v := os.Getenv("WX_RENWU_MU"); v != "" {
		jian.b.renwu_mulu = v
	}
	if zhi := du_peizhi("cpu_yuzhi"); zhi != "" {
		if shu, cuo := strconv.Atoi(zhi); cuo == nil && shu > 0 && shu < 100 {
			jian.b.cpu_yu = shu
		}
	}
	if zhi := du_peizhi("mem_yuzhi"); zhi != "" {
		if shu, cuo := strconv.Atoi(zhi); cuo == nil && shu > 0 && shu < 100 {
			jian.b.mem_yu = shu
		}
	}
	jian.b.gengxin = func() {
		if jian.liebiao != nil {
			jian.liebiao.UpdateNode(2 * time.Second)
		}
	}

	pei := memberlist.DefaultLANConfig()
	pei.Name = ming
	pei.BindPort = duan
	pei.AdvertisePort = duan
	if guangbo != "" {
		pei.AdvertiseAddr = guangbo
	}
	miyao := du_peizhi("miyao")
	if v := os.Getenv("WX_MIYAO"); v != "" {
		miyao = v
	}
	if miyao != "" {
		hes := sha256.Sum256([]byte(miyao))
		yue := hes[:]
		kk, cuo := memberlist.NewKeyring([][]byte{yue}, yue)
		if cuo != nil {
			fmt.Println("keyring 创建失败:", cuo)
		} else {
			pei.Keyring = kk
			fmt.Printf("星间链路加密已开启(密钥取自 miyao 摘要)\n")
		}
	}
	if v := os.Getenv("WX_PROBE_INTERVAL_MS"); v != "" {
		if shu, cuo := strconv.Atoi(v); cuo == nil && shu > 0 {
			pei.ProbeInterval = time.Duration(shu) * time.Millisecond
		}
	}
	if v := os.Getenv("WX_PROBE_TIMEOUT_MS"); v != "" {
		if shu, cuo := strconv.Atoi(v); cuo == nil && shu > 0 {
			pei.ProbeTimeout = time.Duration(shu) * time.Millisecond
		}
	}
	if v := os.Getenv("WX_SUSPICION_MULT"); v != "" {
		if shu, cuo := strconv.Atoi(v); cuo == nil && shu > 0 {
			pei.SuspicionMult = shu
		}
	}
	if v := os.Getenv("WX_RETRANSMIT_MULT"); v != "" {
		if shu, cuo := strconv.Atoi(v); cuo == nil && shu > 0 {
			pei.RetransmitMult = shu
		}
	}
	if v := os.Getenv("WX_GOSSIP_INTERVAL_MS"); v != "" {
		if shu, cuo := strconv.Atoi(v); cuo == nil && shu > 0 {
			pei.GossipInterval = time.Duration(shu) * time.Millisecond
		}
	}
	pei.Events = jian
	pei.Delegate = jian

	liebiao, wu := memberlist.Create(pei)
	if wu != nil {
		fmt.Println("创建失败:", wu)
		os.Exit(1)
	}
	jian.liebiao = liebiao
	jian.jing = xin_jing_jia(liebiao, jian.b)
	ting_zhi := make(chan os.Signal, 1)
	signal.Notify(ting_zhi, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-ting_zhi
		liebiao.Leave(2 * time.Second)
		os.Exit(0)
	}()
	fmt.Printf("[%s] 本节点启动: %s 播报地址 %s 端口 %d 任务端口 %d\n",
		time.Now().Format("15:04:05"), ming, liebiao.LocalNode().Addr, duan, renwu_duan)
	go jian.b.fuwu(renwu_duan)
	go func() {
		for {
			time.Sleep(2 * time.Second)
			liebiao.UpdateNode(2 * time.Second)
		}
	}()

	if lianjie != "" {
		shu, wu := liebiao.Join([]string{lianjie})
		if wu != nil {
			fmt.Println("加入失败:", wu)
		} else {
			fmt.Printf("成功加入集群,共 %d 个节点\n", shu)
		}
	}

	for {
		time.Sleep(5 * time.Second)
		chengyuan := liebiao.Members()
		huo := 0
		for _, x := range chengyuan {
			if x.State == memberlist.StateAlive {
				huo++
			}
		}
		fmt.Printf("[%s] 集群成员 %d 个(存活 %d):", time.Now().Format("15:04:05"), len(chengyuan), huo)
		for _, x := range chengyuan {
			fmt.Printf(" %s=%s", x.Name, x.Addr)
		}
		fmt.Println()
	}
}
