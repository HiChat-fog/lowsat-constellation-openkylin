#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <signal.h>
#include "suanli.skel.h"

static int jixu = 1;
static void tingzhi(int hao) { jixu = 0; }

struct paiming { __u32 pid; char ming[16]; __u64 haoshi_ns; __u64 geci; };

static int bijiao(const void *a, const void *b)
{
    const struct paiming *x = a, *y = b;
    if (y->haoshi_ns > x->haoshi_ns) return 1;
    if (y->haoshi_ns < x->haoshi_ns) return -1;
    return 0;
}

int main(int jianshu, char *canshu[])
{
    int miao = 6;
    if (jianshu > 1) miao = atoi(canshu[1]);

    struct suanli_bpf *qiti = suanli_bpf__open_and_load();
    if (!qiti) { fprintf(stderr, "open_and_load失败\n"); return 1; }
    struct bpf_link *lian = bpf_program__attach(bpf_object__find_program_by_name(qiti->obj, "suanli"));
    if (!lian) { fprintf(stderr, "attach失败: %s\n", strerror(errno)); suanli_bpf__destroy(qiti); return 1; }

    signal(SIGINT, tingzhi);
    printf("算力采集器运行中... 采集 %d 秒\n", miao);
    for (int i = 0; i < miao && jixu; i++) sleep(1);
    if (lian) bpf_link__destroy(lian);

    struct paiming *pai = malloc(sizeof(struct paiming) * 256);
    int ge = 0;
    __u32 jian = 0; __u64 haoshi = 0;
    while (bpf_map__get_next_key(qiti->maps.zongshi_map, &jian, &jian, 4) == 0 && ge < 256) {
        if (bpf_map__lookup_elem(qiti->maps.zongshi_map, &jian, 4, &haoshi, 8, 0) == 0 && haoshi > 0) {
            pai[ge].pid = jian;
            pai[ge].haoshi_ns = haoshi;
            char ming[16] = {0};
            if (bpf_map__lookup_elem(qiti->maps.ming_map, &jian, 4, ming, 16, 0) != 0)
                strcpy(ming, "?");
            strncpy(pai[ge].ming, ming, 15); pai[ge].ming[15] = 0;
            pai[ge].geci = 0;
            ge++;
        }
    }
    qsort(pai, ge, sizeof(struct paiming), bijiao);

    printf("\n== 算力消耗画像(CPU 占用时长 top20) ==\n");
    printf("%-7s %-16s %12s %8s\n", "PID", "进程", "总耗时", "占比");
    __u64 zong = 0;
    for (int i = 0; i < ge; i++) zong += pai[i].haoshi_ns;
    int xian = ge < 20 ? ge : 20;
    for (int i = 0; i < xian; i++)
        printf("%-7u %-16s %8.3f秒 %7.1f%%\n", pai[i].pid, pai[i].ming,
               (double)pai[i].haoshi_ns / 1e9, 100.0 * pai[i].haoshi_ns / zong);
    printf("\n共 %d 个进程被观测到,总CPU时间 %.3f 秒(4核并行,最多约 %.1f 秒)\n",
           ge, (double)zong / 1e9, 4.0 * miao);
    free(pai);
    suanli_bpf__destroy(qiti);
    return 0;
}