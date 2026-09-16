#include <linux/bpf.h>
#include <linux/ptrace.h>
#include <linux/types.h>
#include <bpf/bpf_helpers.h>

struct shijian { unsigned long mingling; };
struct { __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY); __uint(max_entries, 1); __type(key, int); __type(value, struct shijian); } jishu_map SEC(".maps");

SEC("tracepoint/raw_syscalls/sys_enter")
int shuru(struct trace_event_raw_sys_enter *ctx)
{
    struct shijian *zhi;
    int jian = 0;
    zhi = bpf_map_lookup_elem(&jishu_map, &jian);
    if (zhi) zhi->mingling += 1;
    return 0;
}
char _license[] SEC("license") = "GPL";
