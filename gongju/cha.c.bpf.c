#include <linux/bpf.h>
#include <linux/types.h>
#include <bpf/bpf_helpers.h>

struct { __uint(type, BPF_MAP_TYPE_ARRAY); __uint(max_entries, 4); __type(key, __u32); __type(value, __u64); } jieguo_map SEC(".maps");

SEC("raw_tp/sys_enter")
int tan_rawtp(void *ctx)
{
    __u32 jian = 0; __u64 *z = bpf_map_lookup_elem(&jieguo_map, &jian);
    if (z) __sync_fetch_and_add(z, 1);
    return 0;
}
SEC("tracepoint/syscalls/sys_enter_openat")
int tan_tp(struct trace_event_raw_sys_enter *ctx)
{
    __u32 jian = 1; __u64 *z = bpf_map_lookup_elem(&jieguo_map, &jian);
    if (z) __sync_fetch_and_add(z, 1);
    return 0;
}
SEC("kprobe/do_sys_openat2")
int tan_kp(struct pt_regs *ctx)
{
    __u32 jian = 2; __u64 *z = bpf_map_lookup_elem(&jieguo_map, &jian);
    if (z) __sync_fetch_and_add(z, 1);
    return 0;
}
char _license[] SEC("license") = "GPL";