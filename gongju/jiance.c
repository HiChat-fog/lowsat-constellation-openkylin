#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include "peizhi.h"
#include "jiance_yinqing.h"

#define TONG_DAO 5

static const char *dao_ming[TONG_DAO] = {"wendu", "dianya", "dianliu", "zitai", "jiaosudu"};

static struct dao_tai tai[ZUI_DA_DAO];
static int dao_ge_shang = TONG_DAO;

static double gauss(double jun, double biaocha)
{
    double u1 = (double)rand() / RAND_MAX;
    double u2 = (double)rand() / RAND_MAX;
    if (u1 < 1e-9) u1 = 1e-9;
    return jun + biaocha * sqrt(-2.0 * log(u1)) * cos(2.0 * M_PI * u2);
}

static void shengcheng(int t, double zhi[TONG_DAO])
{
    zhi[0] = 20.0 + 3.0 * sin(t * 0.02) + gauss(0, 0.4);
    zhi[1] = 28.0 + 0.5 * sin(t * 0.01) + gauss(0, 0.15);
    zhi[2] = 2.4 + 0.3 * sin(t * 0.03) + gauss(0, 0.06);
    zhi[3] = 15.0 * sin(t * 0.05) + gauss(0, 0.8);
    zhi[4] = 3.0 * sin(t * 0.02 + 1.0) + gauss(0, 0.2);
    if (t >= 260 && t < 380) {
        zhi[0] += 9.0 + (t - 260) * 0.03;
        zhi[1] -= 3.5;
        zhi[2] += 1.2;
    }
    if (t >= 520 && t < 560) {
        for (int j = 0; j < TONG_DAO; j++) zhi[j] += gauss(0, 3.0);
    }
}

static int zice_main(void)
{
    struct { int dao; const char *leixing; int kaishi; int jieshu; } biao_ji[] = {
        {0, "TB", 150, 189},
        {1, "PIAO_YI", 180, 279},
        {2, "FANG_CHA", 360, 399},
        {3, "KA_SI", 460, 539},
    };
    int bao_t[TONG_DAO], hui_t[TONG_DAO], qian[TONG_DAO], lei_zhao[TONG_DAO];
    char bao_lei[TONG_DAO][16];
    for (int j = 0; j < TONG_DAO; j++) {
        bao_t[j] = -1; hui_t[j] = -1; qian[j] = 0; lei_zhao[j] = 0;
        bao_lei[j][0] = 0;
    }
    int wei_ba_wu_bao = 0;
    for (int t = 0; t < 600; t++) {
        double zhi[TONG_DAO];
        zhi[0] = 20.0 + 3.0 * sin(t * 0.02);
        zhi[1] = 28.0 + 0.5 * sin(t * 0.01);
        zhi[2] = 2.4 + 0.3 * sin(t * 0.03);
        zhi[3] = 15.0 * sin(t * 0.05);
        zhi[4] = 3.0 * sin(t * 0.02 + 1.0);
        if (t >= 150 && t < 190) zhi[0] += 10.0;
        if (t >= 180 && t < 280) {
            zhi[1] += (t < 230) ? (t - 180) * 0.08 : (279 - t) * 0.08;
        }
        if (t >= 360 && t < 400) zhi[2] = 2.4 + 1.8 * sin(t * 0.5);
        if (t >= 460 && t < 540) zhi[3] = 15.0 * sin(460 * 0.05);
        for (int j = 0; j < TONG_DAO; j++) tui_yi_dao(&tai[j], zhi[j], t, "ZICE", dao_ming[j]);
        for (int j = 0; j < TONG_DAO; j++) {
            if (!qian[j] && tai[j].guai) {
                bao_t[j] = t;
                snprintf(bao_lei[j], sizeof(bao_lei[j]), "%s", lei_ming[tai[j].leixing_ma - 1]);
            }
            if (qian[j] && !tai[j].guai) hui_t[j] = t;
            for (int m = 0; m < 4; m++) {
                if (biao_ji[m].dao == j && t >= biao_ji[m].kaishi && t <= biao_ji[m].jieshu
                    && tai[j].guai && tai[j].leixing_ma - 1 == m) lei_zhao[j] = 1;
            }
            qian[j] = tai[j].guai;
        }
        if (t > 560) {
            for (int j = 0; j < TONG_DAO; j++) {
                if (tai[j].guai) wei_ba_wu_bao++;
            }
        }
    }
    int huai = 0;
    for (int m = 0; m < 4; m++) {
        int dao = biao_ji[m].dao;
        int zhao_dao = bao_t[dao] >= 0 && bao_t[dao] >= biao_ji[m].kaishi - 2 && bao_t[dao] <= biao_ji[m].jieshu
                       && (strcmp(bao_lei[dao], biao_ji[m].leixing) == 0 || lei_zhao[dao]);
        int hui_lai = hui_t[dao] > biao_ji[m].jieshu && hui_t[dao] <= biao_ji[m].jieshu + 100;
        printf("ZICE %s dao=%s leixing=%s fa_xian=%s(t=%d) hui_fu=%s(t=%d)\n",
               (zhao_dao && hui_lai) ? "PASS" : "FAIL", dao_ming[dao], biao_ji[m].leixing,
               zhao_dao ? "shi" : "fou", bao_t[dao], hui_lai ? "shi" : "fou", hui_t[dao]);
        if (!zhao_dao || !hui_lai) huai = 1;
    }
    if (bao_t[4] >= 0) {
        printf("ZICE FAIL dao=jiaosudu ying wu bao jing\n");
        huai = 1;
    }
    if (wei_ba_wu_bao != 0) {
        printf("ZICE FAIL wei ba wu_bao=%d\n", wei_ba_wu_bao);
        huai = 1;
    }
    if (!huai) {
        printf("ZICE PASS: si lei yi chang jun bei fa xian qie hui fu, gan jing duan wu wu bao\n");
        return 0;
    }
    printf("ZICE FAIL\n");
    return 1;
}

static int shuru_main(void)
{
    char hang[4096];
    int t = 0;
    while (fgets(hang, sizeof(hang), stdin)) {
        double zhi[ZUI_DA_DAO];
        int wei = 0, ge = 0, bu;
        while (ge < ZUI_DA_DAO && sscanf(hang + wei, "%lf%n", &zhi[ge], &bu) == 1) {
            wei += bu;
            ge++;
        }
        if (ge <= 0) continue;
        if (t > 0 && ge < dao_ge_shang) continue;
        if (t == 0) dao_ge_shang = ge;
        for (int j = 0; j < dao_ge_shang; j++) {
            char ming[16];
            snprintf(ming, sizeof(ming), "dao%d", j);
            tui_yi_dao(&tai[j], zhi[j], t, "shuru", ming);
        }
        t++;
    }
    return 0;
}

int main(int jianshu, char *canshu[])
{
    if (jianshu > 1 && strcmp(canshu[1], "--zice") == 0) return zice_main();
    if (jianshu > 1 && strcmp(canshu[1], "--shuru") == 0) return shuru_main();
    char jiedian_guo[64] = "weixing1";
    if (du_zhi("jiedian", jiedian_guo, sizeof(jiedian_guo)) != 0) strcpy(jiedian_guo, "weixing1");
    const char *jiedian = jiedian_guo;
    if (jianshu > 1) jiedian = canshu[1];
    srand(time(NULL) + (int)jiedian[0]);

    int leiji_guai = 0, leiji_huifu = 0;
    printf("设备状态监测启动 节点=%s 滑窗=%d 检测=稳健z+斜率+方差比+卡死\n", jiedian, CHUANG);
    for (int t = 0;; t++) {
        double zhi[TONG_DAO];
        shengcheng(t % 600, zhi);
        for (int j = 0; j < TONG_DAO; j++) {
            int qian_guai = tai[j].guai;
            tui_yi_dao(&tai[j], zhi[j], t, jiedian, dao_ming[j]);
            if (!qian_guai && tai[j].guai) leiji_guai++;
            if (qian_guai && !tai[j].guai) leiji_huifu++;
        }
        if (t % 50 == 0) {
            int chao = 0;
            for (int j = 0; j < TONG_DAO; j++) chao += tai[j].guai;
            printf("REPORT|%s|t=%d|wendu=%.2f|dianya=%.2f|dianliu=%.2f|zitai=%.2f|yichangdaoshu=%d|leiji_guai=%d|leiji_huifu=%d\n",
                   jiedian, t, zhi[0], zhi[1], zhi[2], zhi[3], chao, leiji_guai, leiji_huifu);
        }
        usleep(20000);
    }
    return 0;
}
