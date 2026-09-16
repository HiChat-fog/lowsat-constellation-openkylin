#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

struct { __uint(type, BPF_MAP_TYPE_HASH); __uint(max_entries, 512); __type(key, __u32); __type(value, __u64); } cishu_map SEC(".maps");

SEC("raw_tp/sys_enter")
int shuru(struct bpf_raw_tracepoint_args *canshu)
{
    __u32 mingling = (__u32)canshu->args[1];
    __u64 *zhi = bpf_map_lookup_elem(&cishu_map, &mingling);
    if (zhi) __sync_fetch_and_add(zhi, 1);
    else { __u64 chu = 1; bpf_map_update_elem(&cishu_map, &mingling, &chu, BPF_NOEXIST); }
    return 0;
}
char _license[] SEC("license") = "GPL";
