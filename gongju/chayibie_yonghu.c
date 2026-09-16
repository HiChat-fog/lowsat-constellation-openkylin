#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include "chayibie.skel.h"

int main(void)
{
    struct chayibie_bpf *q = chayibie_bpf__open();
    if (!q) { fprintf(stderr, "open失败\n"); return 1; }
    int e = chayibie_bpf__load(q);
    if (e) { fprintf(stderr, "load失败 errno=%d\n", errno); chayibie_bpf__destroy(q); return 1; }
    printf("load成功(内核接受了探针)\n");

    struct bpf_program *raw = bpf_object__find_program_by_name(q->obj, "cha_rawtp");
    struct bpf_program *tp = bpf_object__find_program_by_name(q->obj, "cha_tp");
    struct bpf_program *kp = bpf_object__find_program_by_name(q->obj, "cha_kp");
    struct bpf_link *l1 = NULL, *l2 = NULL, *l3 = NULL;

    if (raw) { l1 = bpf_program__attach(raw); printf("raw_tp       attach: %s\n", !l1 ? strerror(errno) : "成功"); }
    if (tp)  { l2 = bpf_program__attach(tp);  printf("tracepoint   attach: %s\n", !l2 ? strerror(errno) : "成功"); }
    if (kp)  { l3 = bpf_program__attach(kp);  printf("kprobe       attach: %s\n", !l3 ? strerror(errno) : "成功"); }

    sleep(6);
    const char *name[] = { "raw_tp", "tracepoint", "kprobe" };
    for (int i = 0; i < 3; i++) {
        __u32 jian = i; __u64 z = 0;
        if (!bpf_map__lookup_elem(q->maps.jieguo_map, &jian, 4, &z, 8, 0))
            printf("%s 6秒捕获事件: %lu\n", name[i], z);
    }
    if (l1) bpf_link__destroy(l1);
    if (l2) bpf_link__destroy(l2);
    if (l3) bpf_link__destroy(l3);
    chayibie_bpf__destroy(q);
    return 0;
}