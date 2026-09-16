#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <signal.h>
#include "ziyuan.skel.h"

static int jixu = 1;
static void tingzhi(int hao) { jixu = 0; }

struct paiming { char ming[16]; __u64 cishu; };

static int bijiao(const void *a, const void *b)
{
    const struct paiming *x = a, *y = b;
    if (y->cishu > x->cishu) return 1;
    if (y->cishu < x->cishu) return -1;
    return 0;
}

int main(int jianshu, char *canshu[])
{
    int miao = 6;
    if (jianshu > 1) miao = atoi(canshu[1]);

    struct ziyuan_bpf *qiti = ziyuan_bpf__open_and_load();
    if (!qiti) { fprintf(stderr, "open_and_load失败\n"); return 1; }
    if (ziyuan_bpf__attach(qiti)) { fprintf(stderr, "attach失败: %s\n", strerror(errno)); ziyuan_bpf__destroy(qiti); return 1; }

    signal(SIGINT, tingzhi);
    printf("系统资源采集器运行中... 采集 %d 秒\n", miao);
    for (int i = 0; i < miao && jixu; i++) sleep(1);
    ziyuan_bpf__detach(qiti);

    __u32 jian = 0; __u64 zhi = 0;
    static const char *mings[3] = {"调度切换", "进程执行exec", "进程fork"};
    printf("\n== 系统资源事件统计 ==\n");
    for (int i = 0; i < 3; i++) {
        jian = i; zhi = 0;
        if (bpf_map__lookup_elem(qiti->maps.shijian_map, &jian, 4, &zhi, 8, 0) == 0)
            printf("%-14s: %llu 次\n", mings[i], (unsigned long long)zhi);
    }

    struct paiming *pai = malloc(sizeof(struct paiming) * 256);
    int ge = 0;
    char jianc[16] = {0};
    while (bpf_map__get_next_key(qiti->maps.zhuanhuan_map, &jianc, &jianc, 16) == 0 && ge < 256) {
        if (bpf_map__lookup_elem(qiti->maps.zhuanhuan_map, jianc, 16, &zhi, 8, 0) == 0 && zhi > 0) {
            strncpy(pai[ge].ming, jianc, 15); pai[ge].ming[15] = 0;
            pai[ge].cishu = zhi;
            ge++;
        }
    }
    qsort(pai, ge, sizeof(struct paiming), bijiao);
    printf("\n== CPU调度画像(切换出去最多的进程 top20) ==\n");
    printf("%-16s %10s %6s\n", "进程", "切换次数", "占比");
    __u64 zong = 0;
    for (int i = 0; i < ge; i++) zong += pai[i].cishu;
    int xian = ge < 20 ? ge : 20;
    for (int i = 0; i < xian; i++)
        printf("%-16s %10llu %5.1f%%\n", pai[i].ming, (unsigned long long)pai[i].cishu, 100.0 * pai[i].cishu / zong);
    free(pai);
    ziyuan_bpf__destroy(qiti);
    return 0;
}