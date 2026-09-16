#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <signal.h>
#include "caiji.skel.h"
#include "mingling_tab.h"

static int jixu = 1;
static void tingzhi(int hao) { jixu = 0; }

struct paiming { __u32 mingling; __u64 cishu; };

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

    struct caiji_bpf *qiti = caiji_bpf__open_and_load();
    if (!qiti) { fprintf(stderr, "open_and_load失败\n"); return 1; }
    struct bpf_link *lian = bpf_program__attach(bpf_object__find_program_by_name(qiti->obj, "shuru"));
    if (!lian) { fprintf(stderr, "attach失败: %s\n", strerror(errno)); caiji_bpf__destroy(qiti); return 1; }

    signal(SIGINT, tingzhi);
    printf("系统调用采集器运行中... 采集 %d 秒\n", miao);
    for (int i = 0; i < miao && jixu; i++) sleep(1);
    if (lian) bpf_link__destroy(lian);

    struct paiming *pai = malloc(sizeof(struct paiming) * 512);
    int ge = 0;
    __u32 jian = 0; __u64 zhi = 0;
    while (bpf_map__get_next_key(qiti->maps.cishu_map, &jian, &jian, 4) == 0 && ge < 512) {
        if (bpf_map__lookup_elem(qiti->maps.cishu_map, &jian, 4, &zhi, 8, 0) == 0 && zhi > 0) {
            pai[ge].mingling = jian;
            pai[ge].cishu = zhi;
            ge++;
        }
    }
    qsort(pai, ge, sizeof(struct paiming), bijiao);

    printf("\n== 系统调用统计(按次数排序, top30) ==\n");
    int xian = ge < 30 ? ge : 30;
    __u64 zong = 0;
    for (int i = 0; i < ge; i++) zong += pai[i].cishu;
    printf("共 %d 种系统调用,总次数 %llu\n\n", ge, (unsigned long long)zong);
    printf("%-5s %-16s %10s %6s\n", "编号", "名称", "次数", "占比");
    for (int i = 0; i < xian; i++) {
        const char *ming = pai[i].mingling < 512 && mingling_ming[pai[i].mingling] ? mingling_ming[pai[i].mingling] : "?";
        printf("%-5u %-16s %10llu %5.1f%%\n", pai[i].mingling, ming,
               (unsigned long long)pai[i].cishu, 100.0 * pai[i].cishu / zong);
    }
    free(pai);
    caiji_bpf__destroy(qiti);
    return 0;
}