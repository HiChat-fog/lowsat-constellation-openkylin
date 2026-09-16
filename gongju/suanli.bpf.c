#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

struct { __uint(type, BPF_MAP_TYPE_HASH); __uint(max_entries, 256); __type(key, __u32); __type(value, __u64); } kaishi_map SEC(".maps");
struct { __uint(type, BPF_MAP_TYPE_HASH); __uint(max_entries, 256); __type(key, __u32); __type(value, __u64); } zongshi_map SEC(".maps");
struct { __uint(type, BPF_MAP_TYPE_HASH); __uint(max_entries, 256); __type(key, __u32); __type(value, char[16]); } ming_map SEC(".maps");

SEC("tp/sched/sched_switch")
int suanli(struct trace_event_raw_sched_switch *ctx)
{
    __u32 qian = (__u32)ctx->prev_pid;
    __u32 hou = (__u32)ctx->next_pid;
    __u64 xian = bpf_ktime_get_ns();

    __u64 *kaishi = bpf_map_lookup_elem(&kaishi_map, &qian);
    if (kaishi) {
        __u64 *zong = bpf_map_lookup_elem(&zongshi_map, &qian);
        if (zong) __sync_fetch_and_add(zong, xian - *kaishi);
        else { __u64 chu = xian - *kaishi; bpf_map_update_elem(&zongshi_map, &qian, &chu, BPF_NOEXIST); }
    }
    __u64 *hu = bpf_map_lookup_elem(&kaishi_map, &hou);
    if (hu) *hu = xian;
    else { bpf_map_update_elem(&kaishi_map, &hou, &xian, BPF_ANY); }

    char ming[16];
    bpf_probe_read_kernel(ming, 16, ctx->next_comm);
    char *cun = bpf_map_lookup_elem(&ming_map, &hou);
    if (cun) __builtin_memcpy(cun, ming, 16);
    else bpf_map_update_elem(&ming_map, &hou, ming, BPF_ANY);
    return 0;
}

char _license[] SEC("license") = "GPL";