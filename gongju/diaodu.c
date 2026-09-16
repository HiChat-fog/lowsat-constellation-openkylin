#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define ZUIDA 128
#define JIEDIAN 3

struct renwu {
    int bianhao;
    double daoda;
    double zhixing;
    double kaishi;
    int yi_pai;
};

static double sui_zhishu(double lv)
{
    double u = (double)rand() / RAND_MAX;
    if (u < 1e-9) u = 1e-9;
    return -log(u) / lv;
}

static int bijiao_daoda(const void *a, const void *b)
{
    const struct renwu *x = a, *y = b;
    return x->daoda > y->daoda ? 1 : (x->daoda < y->daoda ? -1 : 0);
}

static double putong_diaodu(struct renwu *rw, int ge)
{
    double jd_done[JIEDIAN] = {0};
    double deng = 0;
    for (int i = 0; i < ge; i++) {
        int xuan = 0;
        for (int j = 1; j < JIEDIAN; j++)
            if (jd_done[j] < jd_done[xuan]) xuan = j;
        double kaishi = rw[i].daoda > jd_done[xuan] ? rw[i].daoda : jd_done[xuan];
        deng += kaishi - rw[i].daoda;
        rw[i].kaishi = kaishi;
        jd_done[xuan] = kaishi + rw[i].zhixing;
    }
    return deng / ge;
}

static double youhua_diaodu(struct renwu *rw, int ge)
{
    double jd_done[JIEDIAN] = {0};
    double xianzai = 0;
    int yi = 0;
    double deng = 0;
    while (yi < ge) {
        int you_kong = -1;
        for (int j = 0; j < JIEDIAN; j++) {
            if (jd_done[j] <= xianzai + 1e-9) { you_kong = j; break; }
        }
        if (you_kong < 0) {
            double zui_zao = jd_done[0];
            for (int j = 1; j < JIEDIAN; j++)
                if (jd_done[j] < zui_zao) zui_zao = jd_done[j];
            xianzai = zui_zao;
            continue;
        }
        int xuan = -1;
        double zuiduan = 1e18;
        for (int i = 0; i < ge; i++) {
            if (!rw[i].yi_pai && rw[i].daoda <= xianzai + 1e-9 && rw[i].zhixing < zuiduan) {
                zuiduan = rw[i].zhixing;
                xuan = i;
            }
        }
        if (xuan < 0) {
            double zui_wan = 1e18;
            for (int i = 0; i < ge; i++) {
                if (!rw[i].yi_pai && rw[i].daoda < zui_wan) zui_wan = rw[i].daoda;
            }
            xianzai = zui_wan;
            continue;
        }
        deng += xianzai - rw[xuan].daoda;
        rw[xuan].kaishi = xianzai;
        rw[xuan].yi_pai = 1;
        jd_done[you_kong] = xianzai + rw[xuan].zhixing;
        yi++;
    }
    return deng / ge;
}

int main(int jianshu, char *canshu[])
{
    int zice = 0;
    if (jianshu > 1 && strcmp(canshu[1], "--zice") == 0) zice = 1;
    int ge = 30;
    if (jianshu > 1 && !zice) ge = atoi(canshu[1]);
    int lun = 60;
    if (jianshu > 2 && !zice) lun = atoi(canshu[2]);
    if (zice) { ge = 60; lun = 60; }

    double he_p = 0, he_y = 0;
    double lv = 2.0;
    if (jianshu > 3 && !zice) lv = atof(canshu[3]);
    double zui_jiang = 1e18;
    for (int r = 0; r < lun; r++) {
        srand(20260829 + r * 7919);
        struct renwu rw[ZUIDA];
        double shike = 0;
        for (int i = 0; i < ge; i++) {
            shike += sui_zhishu(lv);
            rw[i].bianhao = i;
            rw[i].daoda = shike;
            rw[i].zhixing = 0.5 + (double)rand() / RAND_MAX * 5.0;
            rw[i].kaishi = 0;
            rw[i].yi_pai = 0;
        }
        qsort(rw, ge, sizeof(struct renwu), bijiao_daoda);
        for (int i = 0; i < ge; i++) rw[i].yi_pai = 0;
        double dan_p = putong_diaodu(rw, ge);
        for (int i = 0; i < ge; i++) rw[i].yi_pai = 0;
        double dan_y = youhua_diaodu(rw, ge);
        he_p += dan_p;
        he_y += dan_y;
        if (dan_p - dan_y < zui_jiang) zui_jiang = dan_p - dan_y;
    }
    double p = he_p / lun, y = he_y / lun;
    printf("任务数=%d 节点数=%d 模拟轮数=%d\n", ge, JIEDIAN, lun);
    printf("普通调度(FCFS+最闲节点)平均等待: %.3f 秒\n", p);
    printf("优化调度(SJF+最早空闲) 平均等待: %.3f 秒\n", y);
    printf("等待时间降幅: %.1f%% (命题要求>=10%%)\n", 100.0 * (p - y) / p);
    if (zice) {
        if (y > 0 && y < p && zui_jiang > 0) {
            printf("ZICE PASS: 优化调度恒优于普通调度,%d 轮全部成立\n", lun);
            return 0;
        }
        printf("ZICE FAIL: 存在优化不优于普通的轮次\n");
        return 1;
    }
    return 0;
}