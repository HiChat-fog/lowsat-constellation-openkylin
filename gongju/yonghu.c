#include <stdio.h>
#include <unistd.h>
#include <signal.h>
#include <stdlib.h>
#include "caiji.skel.h"

static int pao = 1;
static void ting(int xin) { pao = 0; }

int main(void)
{
    struct caiji_bpf *qiti = caiji_bpf__open_and_load();
    if (!qiti) { fprintf(stderr, "打开或加载失败\n"); return 1; }
    if (caiji_bpf__attach(qiti)) { fprintf(stderr, "挂载失败\n"); return 1; }
    signal(SIGINT, ting);
    printf("采集运行中... 按Ctrl+C结束\n");
    while (pao) { sleep(1); }
    printf("\n== 系统调用统计(前20项) ==\n");
    __u32 mingling = 0; __u64 zhi; int n = 0;
    while (bpf_map__get_next_key(qiti->maps.cishu_map, &mingling, &mingling, 4) == 0 && n < 20) {
        if (bpf_map__lookup_elem(qiti->maps.cishu_map, &mingling, 4, &zhi, 8, 0) == 0)
            printf("syscall %3u: %lu ci\n", mingling, zhi);
        n++;
    }
    caiji_bpf__destroy(qiti);
    return 0;
}
