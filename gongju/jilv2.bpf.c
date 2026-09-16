#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

SEC("tracepoint/raw_syscalls/sys_enter")
int shuru2(void *ctx)
{
    return 0;
}
char _license[] SEC("license") = "GPL";
