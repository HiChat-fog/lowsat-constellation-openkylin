#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

struct { __uint(type, BPF_MAP_TYPE_HASH); __uint(max_entries, 256); __type(key, char[16]); __type(value, __u64); } zhuanhuan_map SEC(".maps");
struct { __uint(type, BPF_MAP_TYPE_ARRAY); __uint(max_entries, 4); __type(key, __u32); __type(value, __u64); } shijian_map SEC(".maps");

SEC("tp/sched/sched_switch")
int zhuanhuan(struct trace_event_raw_sched_switch *ctx)
{
    char ming[16];
    bpf_probe_read_kernel(ming, 16, ctx->prev_comm);
    __u64 *ji = bpf_map_lookup_elem(&zhuanhuan_map, ming);
    if (ji) __sync_fetch_and_add(ji, 1);
    else { __u64 chu = 1; bpf_map_update_elem(&zhuanhuan_map, ming, &chu, BPF_NOEXIST); }
    __u32 jian = 0; __u64 *z = bpf_map_lookup_elem(&shijian_map, &jian);
    if (z) __sync_fetch_and_add(z, 1);
    return 0;
}

SEC("tp/sched/sched_process_exec")
int zhixing(struct trace_event_raw_sched_process_exec *ctx)
{
    __u32 jian = 1; __u64 *z = bpf_map_lookup_elem(&shijian_map, &jian);
    if (z) __sync_fetch_and_add(z, 1);
    return 0;
}

SEC("tp/sched/sched_process_fork")
int fanzhi(struct trace_event_raw_sched_process_fork *ctx)
{
    __u32 jian = 2; __u64 *z = bpf_map_lookup_elem(&shijian_map, &jian);
    if (z) __sync_fetch_and_add(z, 1);
    return 0;
}

char _license[] SEC("license") = "GPL";