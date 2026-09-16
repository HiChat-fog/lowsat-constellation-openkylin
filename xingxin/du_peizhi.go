package main

import (
	"os"
	"strings"
)

func du_peizhi(key string) string {
	data, wu := os.ReadFile("/etc/weixing/weixing.conf")
	if wu != nil {
		return ""
	}
	for _, hang := range strings.Split(string(data), "\n") {
		weizhi := strings.Index(hang, "=")
		if weizhi < 0 {
			continue
		}
		ming := strings.TrimSpace(hang[:weizhi])
		zhi := strings.TrimSpace(hang[weizhi+1:])
		if ming == key {
			return zhi
		}
	}
	return ""
}
