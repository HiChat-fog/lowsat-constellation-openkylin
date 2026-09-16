#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <sys/resource.h>
#include <linux/bpf.h>
#include <linux/errno.h>
#include <linux/filter.h>
#include <stdlib.h>
#include <errno.h>
#include "jiazaijian.h"

#ifndef SYS_bpf
#define SYS_bpf 280
#endif

static int cha_mingling(enum bpf_cmd mingling, union bpf_attr *canshu)
{
    return syscall(SYS_bpf, mingling, canshu, sizeof(*canshu));
}

static int jiazai(int leixing, const char *ming)
{
    union bpf_attr baocan = {};
    baocan.prog_type = leixing;
    baocan.insn_cnt = sizeof(zl) / sizeof(struct bpf_insn);
    baocan.insns = (unsigned long) zl;
    baocan.license = (unsigned long) "GPL";
    baocan.log_level = 1;
    baocan.log_size = 65536;
    char *rizhi = malloc(65536);
    memset(rizhi, 0, 65536);
    baocan.log_buf = (unsigned long) rizhi;
    int fd = cha_mingling(BPF_PROG_LOAD, &baocan);
    if (fd < 0) {
        fprintf(stderr, "[%s] 类型%d 失败: %s\n日志[%zu]字节: %s\n", ming, leixing, strerror(errno), strlen(rizhi), rizhi);
        return 1;
    }
    printf("[%s] 类型%d 成功 fd=%d\n", ming, leixing, fd);
    close(fd);
    return 0;
}

int main(void)
{
    struct rlimit xz = { RLIM_INFINITY, RLIM_INFINITY };
    setrlimit(RLIMIT_MEMLOCK, &xz);
    jiazai(BPF_PROG_TYPE_SOCKET_FILTER, "socket_filter");
    jiazai(BPF_PROG_TYPE_TRACEPOINT, "tracepoint");
    jiazai(BPF_PROG_TYPE_KPROBE, "kprobe");
    return 0;
}
