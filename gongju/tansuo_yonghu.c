#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include "tansuo.skel.h"

int main(void)
{
    struct tansuo_bpf *q = tansuo_bpf__open();
    if (!q) { fprintf(stderr, "open失败\n"); return 1; }
    int e = tansuo_bpf__load(q);
    if (e) { fprintf(stderr, "load失败 errno=%d\n", errno); tansuo_bpf__destroy(q); return 1; }
    printf("load成功(内核接受了这两个程序)\n");
    struct bpf_program *raw = bpf_object__find_program_by_name(q->obj, "tan_rawtp");
    struct bpf_program *perf = bpf_object__find_program_by_name(q->obj, "tan_perf");
    int l1 = -1, l2 = -1;
    if (raw) { l1 = bpf_program__attach(raw); printf("raw_tp attach: %s\n", l1 < 0 ? strerror(errno) : "成功"); }
    if (perf) { l2 = bpf_program__attach(perf); printf("perf_event attach: %s\n", l2 < 0 ? strerror(errno) : "成功"); }
    sleep(6);
    __u32 jian = 0; __u64 z = 0;
    if (raw && l1 >= 0 && !bpf_map__lookup_elem(q->maps.jieguo_map, &jian, 4, &z, 8, 0))
        printf("raw_tp 6秒捕获事件: %lu\n", z);
    jian = 1; z = 0;
    if (perf && l2 >= 0 && !bpf_map__lookup_elem(q->maps.jieguo_map, &jian, 4, &z, 8, 0))
        printf("perf_event 6秒捕获事件: %lu\n", z);
    if (l1 >= 0) bpf_link__destroy(l1);
    if (l2 >= 0) bpf_link__destroy(l2);
    tansuo_bpf__destroy(q);
    return 0;
}
