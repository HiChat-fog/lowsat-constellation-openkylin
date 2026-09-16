#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

struct { __uint(type, BPF_MAP_TYPE_HASH); __uint(max_entries, 512); __type(key, __u32); __type(value, __u64); } cishu_map SEC(".maps");
struct { __uint(type, BPF_MAP_TYPE_HASH); __uint(max_entries, 256); __type(key, char[16]); __type(value, __u64); } zhuanhuan_map SEC(".maps");
struct { __uint(type, BPF_MAP_TYPE_HASH); __uint(max_entries, 256); __type(key, __u32); __type(value, __u64); } kaishi_map SEC(".maps");
struct { __uint(type, BPF_MAP_TYPE_HASH); __uint(max_entries, 256); __type(key, __u32); __type(value, __u64); } suanli_map SEC(".maps");
struct { __uint(type, BPF_MAP_TYPE_HASH); __uint(max_entries, 256); __type(key, __u32); __type(value, char[16]); } ming_map SEC(".maps");
struct { __uint(type, BPF_MAP_TYPE_ARRAY); __uint(max_entries, 8); __type(key, __u32); __type(value, __u64); } shijian_map SEC(".maps");
struct { __uint(type, BPF_MAP_TYPE_ARRAY); __uint(max_entries, 4); __type(key, __u32); __type(value, __u64); } diao_map SEC(".maps");

SEC("raw_tp/sys_enter")
int guan_yw(struct bpf_raw_tracepoint_args *canshu)
{
    __u32 mingling = (__u32)canshu->args[1];
    __u64 *zhi = bpf_map_lookup_elem(&cishu_map, &mingling);
    if (zhi) __sync_fetch_and_add(zhi, 1);
    else if (bpf_map_update_elem(&cishu_map, &mingling, &(__u64){1}, BPF_NOEXIST)) {
        __u32 jian3 = 3;
        __u64 *d = bpf_map_lookup_elem(&diao_map, &jian3);
        if (d) __sync_fetch_and_add(d, 1);
    }
    return 0;
}

SEC("tp/sched/sched_switch")
int guan_zy(struct trace_event_raw_sched_switch *ctx)
{
    char ming[16];
    bpf_probe_read_kernel(ming, 16, ctx->prev_comm);
    __u64 *ji = bpf_map_lookup_elem(&zhuanhuan_map, ming);
    if (ji) __sync_fetch_and_add(ji, 1);
    else { __u64 chu = 1; bpf_map_update_elem(&zhuanhuan_map, ming, &chu, BPF_NOEXIST); }

    __u32 jian0 = 0; __u64 *z0 = bpf_map_lookup_elem(&shijian_map, &jian0);
    if (z0) __sync_fetch_and_add(z0, 1);

    __u32 qian = (__u32)ctx->prev_pid;
    __u32 hou = (__u32)ctx->next_pid;
    __u64 xian = bpf_ktime_get_ns();
    __u64 *kaishi = bpf_map_lookup_elem(&kaishi_map, &qian);
    if (kaishi) {
        __u64 *zong = bpf_map_lookup_elem(&suanli_map, &qian);
        if (zong) __sync_fetch_and_add(zong, xian - *kaishi);
        else { __u64 chu = xian - *kaishi; bpf_map_update_elem(&suanli_map, &qian, &chu, BPF_NOEXIST); }
    }
    __u64 *hu = bpf_map_lookup_elem(&kaishi_map, &hou);
    if (hu) *hu = xian;
    else bpf_map_update_elem(&kaishi_map, &hou, &xian, BPF_ANY);

    char ming2[16];
    bpf_probe_read_kernel(ming2, 16, ctx->next_comm);
    char *cun = bpf_map_lookup_elem(&ming_map, &hou);
    if (cun) __builtin_memcpy(cun, ming2, 16);
    else bpf_map_update_elem(&ming_map, &hou, ming2, BPF_ANY);
    return 0;
}

SEC("tp/sched/sched_process_exec")
int guan_zhx(struct trace_event_raw_sched_process_exec *ctx)
{
    __u32 jian1 = 1; __u64 *z1 = bpf_map_lookup_elem(&shijian_map, &jian1);
    if (z1) __sync_fetch_and_add(z1, 1);
    return 0;
}

SEC("tp/sched/sched_process_fork")
int guan_fz(struct trace_event_raw_sched_process_fork *ctx)
{
    __u32 jian2 = 2; __u64 *z2 = bpf_map_lookup_elem(&shijian_map, &jian2);
    if (z2) __sync_fetch_and_add(z2, 1);
    return 0;
}

SEC("raw_tp/sched_process_exit")
int guan_tui(struct bpf_raw_tracepoint_args *canshu)
{
    __u32 pid = (__u32)bpf_get_current_pid_tgid();
    bpf_map_delete_elem(&kaishi_map, &pid);
    bpf_map_delete_elem(&suanli_map, &pid);
    bpf_map_delete_elem(&ming_map, &pid);
    return 0;
}

char _license[] SEC("license") = "GPL";