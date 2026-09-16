CC = riscv64-linux-gnu-gcc
CLANG ?= clang
BPFTOOL ?= bpftool
GO = $(shell command -v go 2>/dev/null || echo /usr/local/go/bin/go)
LIBBPF_DIR ?= /tmp/openkylin-kernel/tools/lib/bpf
SQLITE_A ?= /tmp/sqlite_rv/usr/lib/riscv64-linux-gnu/libsqlite3.a
X64_INC ?= /usr/include/x86_64-linux-gnu
BAN_BEN = $(shell git describe --always --dirty 2>/dev/null || echo dev)

USER_LIBS = $(LIBBPF_DIR)/libbpf.a -lz -lelf -lzstd -lm
AGENT_LIBS = $(USER_LIBS) $(SQLITE_A) -lm -ldl -lpthread
GONGJU_BPF = caiji ziyuan suanli chayibie tansuo

all: chengwu/agent_yonghu chengwu/jiance chengwu/dianyuan chengwu/jiankang chengwu/diaodu chengwu/xingxin_riscv64 $(GONGJU_BPF:%=chengwu/%_yonghu)

agent/agent.bpf.o: agent/agent.bpf.c gongju/vmlinux.h
	$(CLANG) -g -O2 -target bpf -I$(X64_INC) -Igongju -c $< -o $@

agent/agent.skel.h: agent/agent.bpf.o
	$(BPFTOOL) gen skeleton $< > $@

chengwu/agent_yonghu: agent/agent_yonghu.c agent/zhushou.h agent/agent.skel.h agent/peizhi.h agent/mingling_tab.h
	$(CC) -static -O2 -Wall -DBAN_BEN=\"$(BAN_BEN)\" -Iagent -Igongju -I$(LIBBPF_DIR) agent/agent_yonghu.c $(AGENT_LIBS) -o $@

gongju/%.bpf.o: gongju/%.bpf.c gongju/vmlinux.h
	$(CLANG) -g -O2 -target bpf -I$(X64_INC) -Igongju -c $< -o $@

gongju/%.skel.h: gongju/%.bpf.o
	$(BPFTOOL) gen skeleton $< > $@

chengwu/%_yonghu: gongju/%_yonghu.c gongju/%.skel.h gongju/%.bpf.o gongju/peizhi.h
	$(CC) -static -O2 -Wall -Iagent -Igongju -I$(LIBBPF_DIR) gongju/$*_yonghu.c $(USER_LIBS) -o $@

chengwu/jiance: gongju/jiance.c gongju/jiance_yinqing.h gongju/peizhi.h
	$(CC) -static -O2 gongju/jiance.c -lm -o $@

chengwu/dianyuan: gongju/dianyuan.c gongju/jiance_yinqing.h gongju/peizhi.h
	$(CC) -static -O2 gongju/dianyuan.c -lm -o $@

chengwu/jiankang: gongju/jiankang.c
	$(CC) -static -O2 gongju/jiankang.c -lm -o $@

chengwu/diaodu: gongju/diaodu.c
	$(CC) -static -O2 gongju/diaodu.c -lm -o $@

chengwu/xingxin_riscv64: xingxin/main.go xingxin/renwu.go xingxin/du_peizhi.go xingxin/go.mod xingxin/go.sum
	cd xingxin && GOOS=linux GOARCH=riscv64 CGO_ENABLED=0 $(GO) build -trimpath -ldflags "-s -w" -o ../chengwu/xingxin_riscv64 .

GCC_BEN = gcc

ceshi: ceshi-c ceshi-py ceshi-go ceshi-jing

/tmp/ce_zhushou: ceshi/ce_zhushou.c agent/zhushou.h
	$(GCC_BEN) -O2 -Wall -Iagent ceshi/ce_zhushou.c -o $@

/tmp/jz: gongju/jiance.c gongju/peizhi.h
	$(GCC_BEN) -O2 -Wall gongju/jiance.c -lm -o $@

/tmp/dz: gongju/diaodu.c
	$(GCC_BEN) -O2 -Wall gongju/diaodu.c -lm -o $@

ceshi-c: /tmp/ce_zhushou /tmp/jz /tmp/dz
	/tmp/ce_zhushou

ceshi-py: /tmp/ce_zhushou /tmp/jz /tmp/dz
	python3 -m pytest ceshi/ -q

ceshi-go:
	cd xingxin && $(GO) test -race .
	cd xingxin && $(GO) vet .
	(cd xingxin && $(GO) run honnef.co/go/tools/cmd/staticcheck@latest . ) || echo tiaoguo staticcheck

clean:
	rm -f agent/agent.bpf.o agent/agent.skel.h
	rm -f gongju/*.bpf.o gongju/*.skel.h
	rm -f chengwu/*

.PHONY: all ceshi ceshi-c ceshi-py ceshi-go ceshi-jing clean

ceshi-jing:
	command -v shellcheck >/dev/null && shellcheck jiaoben/*.sh xingxin/ce_fault.sh || echo tiaoguo shellcheck
	command -v cppcheck >/dev/null && cppcheck --enable=warning --error-exitcode=2 agent/agent_yonghu.c gongju/jiance.c gongju/dianyuan.c gongju/jiankang.c gongju/diaodu.c || echo tiaoguo cppcheck
