package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

type fu_zai_xin struct {
	Cpu      float64 `json:"cpu"`
	Neicun   int     `json:"neicun"`
	RenwuShu int     `json:"renwu_shu"`
	LeiJi    int64   `json:"leiji"`
}

func yu_ce_fen(fu fu_zai_xin, canliang_s uint64) float64 {
	fen := fu_zai_zhi(fu)
	if canliang_s > 0 && fu.LeiJi > 0 {
		bi := float64(fu.LeiJi) / float64(canliang_s)
		if bi > 1.0 {
			bi = 1.0
		}
		fen += 30.0 * bi
	}
	return fen
}

func du_cpu() (float64, float64, bool) {
	nei, cuo := os.ReadFile("/proc/stat")
	if cuo != nil {
		return 0, 0, false
	}
	for _, hang := range strings.Split(string(nei), "\n") {
		if !strings.HasPrefix(hang, "cpu ") {
			continue
		}
		ge := strings.Fields(hang[4:])
		if len(ge) < 4 {
			return 0, 0, false
		}
		var zong float64
		for _, zi := range ge {
			zhi, cuo := strconv.ParseFloat(zi, 64)
			if cuo != nil {
				return 0, 0, false
			}
			zong += zhi
		}
		xian, _ := strconv.ParseFloat(ge[3], 64)
		if len(ge) > 4 {
			if duo, cuo := strconv.ParseFloat(ge[4], 64); cuo == nil {
				xian += duo
			}
		}
		return zong, xian, true
	}
	return 0, 0, false
}

func du_neicun() int {
	nei, cuo := os.ReadFile("/proc/meminfo")
	if cuo != nil {
		return 0
	}
	zong, keyong := 0, -1
	for _, hang := range strings.Split(string(nei), "\n") {
		if strings.HasPrefix(hang, "MemTotal:") {
			fmt.Sscanf(hang, "MemTotal: %d", &zong)
		}
		if strings.HasPrefix(hang, "MemAvailable:") {
			fmt.Sscanf(hang, "MemAvailable: %d", &keyong)
			break
		}
	}
	if zong <= 0 || keyong < 0 {
		return 0
	}
	return (zong - keyong) * 100 / zong
}

func fu_zai_zhi(fu fu_zai_xin) float64 {
	return fu.Cpu*0.6 + float64(fu.Neicun)*0.4
}
