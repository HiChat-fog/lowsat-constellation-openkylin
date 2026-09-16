#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include "peizhi.h"
#include "jiance_yinqing.h"

#define DAO_SHU 6
#define YIN_SHU 5
#define ZHOU_QI 400
#define TONG_KUAN 4
#define TONG_SHU (ZHOU_QI / TONG_KUAN)
#define DI_YING_KAI 150
#define DI_YING_HE 273
#define GUODU_SHU 14
#define XUE_QI ZHOU_QI
#define E_RONG 12.0
#define U0 23.6
#define U_FU 3.0
#define R_JI 0.030
#define R_ZENG 0.018
#define P0 93.0
#define FU_ZAI 55.0
#define DIAN_ZU_ZENG 0.15
#define CHONG_WU 25
#define SEU_BEI 8.0
#define GUANG_BI 0.8
#define YING_BEI 8.0
#define WEN_XIAN 42.0

static const char *dao_ming[DAO_SHU] = {"u_bus", "u_bat", "i_bat", "i_load", "p_pv", "w_pcu"};
static const int yin_dao[YIN_SHU] = {0, 1, 2, 3, 5};
static const double tong_floor[YIN_SHU] = {0.3, 0.3, 0.3, 0.1, 0.5};

struct dianyuan_tai {
    struct dao_tai yin[YIN_SHU];
    double tong_zhong[TONG_SHU][YIN_SHU];
    double tong_mad[TONG_SHU][YIN_SHU];
    int tong_fang[TONG_SHU][YIN_SHU];
    int guodu_zhi;
    int shang_shi;
    int shang_zhao;
    double soc;
    double r_dong;
    double r_ji;
    double r_man;
    double r_nei[8];
    int r_ge;
    int xunhuan;
    double dod_ben;
    double ben_feng;
    double shang_feng;
    int guang_can;
    int zu_ji;
    int zu_guai;
    int wen_ji;
    int wen_guai;
    int muxian_ji;
    int muxian_ji_hui;
    int muxian_guai;
    int chong_wu_ji;
    int chong_wu_guai;
    int guo_dian_guai;
    int ji_duan_seu[YIN_SHU];
    int ji_qian_seu[YIN_SHU];
    int dai_seu[YIN_SHU];
    double dai_seu_zhi[YIN_SHU];
    int wai_shu;
    int soc_chu;
    int jia_za;
    char biao_qian[YIN_SHU][24];
    int biao_guai[YIN_SHU];
    int guodu_bao;
};

static struct dianyuan_tai dy;
static const char *wo_jiedian = "weixing1";
static FILE *shi_chu;

static double gauss(double jun, double biaocha)
{
    double u1 = (double)rand() / RAND_MAX;
    double u2 = (double)rand() / RAND_MAX;
    if (u1 < 1e-9) u1 = 1e-9;
    return jun + biaocha * sqrt(-2.0 * log(u1)) * cos(2.0 * M_PI * u2);
}

static void shi_jian_xing(const char *geshi, ...)
{
    va_list c;
    va_start(c, geshi);
    vfprintf(shi_chu, geshi, c);
    va_end(c);
}

static void yu_gua_zhong(const char *dongzuo, int t_hao, const char *dao_ming_chen, double zhi)
{
    int c = -1;
    for (int j = 0; j < YIN_SHU; j++) {
        if (strcmp(dao_ming_chen, dao_ming[yin_dao[j]]) == 0) { c = j; break; }
    }
    if (c < 0) return;
    if (strcmp(dongzuo, "ALARM") == 0) {
        if (t_hao < dy.guodu_zhi) {
            dy.guodu_bao++;
            return;
        }
        const char *qian = NULL;
        int d = yin_dao[c];
        if (strcmp(dao_ming_chen, "i_bat") == 0 && dy.shang_shi == 0) qian = "CHONGDIAN_YICHANG";
        else if (strcmp(dao_ming_chen, "u_bat") == 0 && zhi > 0 && dy.shang_shi == 0) qian = "CHONGDIAN_YICHANG";
        if (qian) {
            dy.biao_guai[c] = 1;
            snprintf(dy.biao_qian[c], sizeof(dy.biao_qian[c]), "%s", qian);
            shi_jian_xing("ALARM|%s|t=%d|leixing=DIANYU|dao=%s|label=%s|zhi=%.3f\n",
                          wo_jiedian, t_hao, dao_ming[d], qian, zhi);
        }
    } else if (strcmp(dongzuo, "RECOVER") == 0 && dy.biao_guai[c]) {
        shi_jian_xing("RECOVER|%s|t=%d|leixing=DIANYU|dao=%s|label=%s\n",
                      wo_jiedian, t_hao, dao_ming[yin_dao[c]], dy.biao_qian[c]);
        dy.biao_guai[c] = 0;
    }
}

static void dy_chu_shi(void)
{
    memset(&dy, 0, sizeof(dy));
    dy.soc = 0.9;
    dy.shang_shi = -1;
    dy.shang_zhao = -1;
    dy.guodu_zhi = 30;
    yin_qing_gua_zhong = yu_gua_zhong;
}

static double soh_zhi(void)
{
    if (dy.r_ji <= 0 || dy.r_dong <= 0) return 100.0;
    double soh = 100.0 * (1.0 - 0.75 * (dy.r_dong - dy.r_ji) / dy.r_ji);
    return soh < 0 ? 0 : (soh > 100 ? 100 : soh);
}

static double rul_zhi(void)
{
    int ge = dy.r_ge < 8 ? dy.r_ge : 8;
    if (ge < 3) return -1.0;
    double sx = 0, sy = 0, sxx = 0, sxy = 0;
    int qi = dy.r_ge - ge;
    for (int i = 0; i < ge; i++) {
        double x = qi + i, y = dy.r_nei[(qi + i) % 8];
        sx += x; sy += y; sxx += x * x; sxy += x * y;
    }
    double mu = ge * sxx - sx * sx;
    if (fabs(mu) < 1e-12) return -1.0;
    double xie = (ge * sxy - sx * sy) / mu;
    if (xie <= 1e-9) return -1.0;
    double cha = dy.r_ji * 1.8 - dy.r_nei[(dy.r_ge - 1) % 8];
    if (cha <= 0) return 0.0;
    return cha / xie;
}

static void bao_gao_yi_hang(int t, const double zhi[DAO_SHU], FILE *mu)
{
    fprintf(mu, "REPORT|%s|t=%d|soc=%.3f|u_bus=%.2f|i_bat=%.2f|r_mo=%.1f|soh=%.1f|xunhuan=%d|dod=%.2f|rul=%.0f\n",
            wo_jiedian, t, dy.soc, zhi[0], zhi[2],
            dy.r_dong > 0 ? dy.r_dong * 1000.0 : 0.0,
            soh_zhi(), dy.xunhuan, dy.dod_ben, rul_zhi());
}

static void tui_yi_bang(int t, const double zhi[DAO_SHU])
{
    int zhao = zhi[4] > 10.0;
    if (dy.shang_zhao >= 0 && zhao != dy.shang_zhao)
        dy.guodu_zhi = t + GUODU_SHU;
    if (dy.shang_zhao == 0 && zhao == 1) {
        dy.xunhuan++;
        if (dy.ben_feng > 0 && dy.shang_feng > 0) {
            if (dy.ben_feng < GUANG_BI * dy.shang_feng && !dy.guang_can) {
                dy.guang_can = 1;
                shi_jian_xing("ALARM|%s|t=%d|leixing=DIANYU|dao=p_pv|label=GUANGFU_SHUAIJIAN|zhi=%.3f\n",
                              wo_jiedian, t, dy.ben_feng);
            }
            if (dy.ben_feng > dy.shang_feng * 0.97 && dy.guang_can) {
                dy.guang_can = 0;
                shi_jian_xing("RECOVER|%s|t=%d|leixing=DIANYU|dao=p_pv|label=GUANGFU_SHUAIJIAN\n",
                              wo_jiedian, t);
            }
            if (dy.ben_feng < dy.shang_feng) dy.shang_feng = (dy.ben_feng + dy.shang_feng) / 2;
        } else if (dy.ben_feng > 0) {
            dy.shang_feng = dy.ben_feng;
        }
        if (dy.r_dong > 0) {
            dy.r_nei[dy.r_ge % 8] = dy.r_dong;
            dy.r_ge++;
        }
        dy.ben_feng = 0.0;
    }
    dy.shang_zhao = zhao;
    dy.shang_shi = (t < dy.guodu_zhi) ? 1 : (zhao ? 0 : 2);

    int tong = (t % ZHOU_QI) / TONG_KUAN;
    for (int j = 0; j < YIN_SHU; j++) {
        int c = yin_dao[j];
        double can = zhi[c] - dy.tong_zhong[tong][j];
        double gai_mad = dy.tong_mad[tong][j] > tong_floor[j] ? dy.tong_mad[tong][j] : tong_floor[j];
        int shi_ji = t >= dy.guodu_zhi && dy.tong_fang[tong][j] && fabs(can) > SEU_BEI * gai_mad;
        if (dy.dai_seu[j] && !shi_ji && !dy.ji_qian_seu[j] && dy.ji_duan_seu[j]) {
            shi_jian_xing("SEU|%s|t=%d|dao=%s|zhi=%.3f\n",
                          wo_jiedian, t, dao_ming[c], dy.dai_seu_zhi[j]);
            dy.dai_seu[j] = 0;
        }
        dy.ji_qian_seu[j] = dy.ji_duan_seu[j];
        dy.ji_duan_seu[j] = shi_ji;
        if (shi_ji) {
            dy.dai_seu[j] = 1;
            dy.dai_seu_zhi[j] = zhi[c];
        }
        if (!dy.tong_fang[tong][j]) {
            dy.tong_zhong[tong][j] = zhi[c];
            dy.tong_fang[tong][j] = 1;
            can = 0.0;
        } else if (t < dy.guodu_zhi) {
            can = fabs(can) > YING_BEI * gai_mad
                      ? (can > 0 ? 6.0 * gai_mad : -6.0 * gai_mad)
                      : 0.0;
        } else {
            if (fabs(can) > 6.0 * gai_mad)
                can = can > 0 ? 6.0 * gai_mad : -6.0 * gai_mad;
            else {
                dy.tong_zhong[tong][j] += 0.25 * (zhi[c] - dy.tong_zhong[tong][j]);
                dy.tong_mad[tong][j] += 0.25 * (fabs(can) - dy.tong_mad[tong][j]);
            }
            if (dy.jia_za) can += gauss(0, 0.5 * tong_floor[j]);
        }
        tui_yi_dao(&dy.yin[j], can, t, wo_jiedian, dao_ming[c]);
    }

    if (dy.wai_shu) {
        if (!dy.soc_chu) {
            dy.soc = (zhi[1] - U0) / U_FU;
            if (dy.soc > 1.0) dy.soc = 1.0;
            if (dy.soc < 0.2) dy.soc = 0.2;
            dy.soc_chu = 1;
        }
        dy.soc += zhi[2] * zhi[1] / 3600.0 / E_RONG;
        if (dy.soc > 1.0) dy.soc = 1.0;
        if (dy.soc < 0.0) dy.soc = 0.0;
    }

    if (dy.shang_shi == 2 && zhi[2] < -1.0) {
        double ocv = U0 + U_FU * dy.soc;
        double r_gu = (ocv - zhi[1]) / (-zhi[2]);
        if (getenv("DY_DEBUG") && (t % 50 == 0))
            fprintf(stderr, "t=%d soc=%.3f ocv=%.3f u_bat=%.3f i=%.2f r_gu=%.4f r_dong=%.4f r_ji=%.4f r_man=%.4f zu_ji=%d\n",
                    t, dy.soc, ocv, zhi[1], zhi[2], r_gu, dy.r_dong, dy.r_ji, dy.r_man, dy.zu_ji);
        if (r_gu > 1e-4 && r_gu < 1.0) {
            dy.r_dong = dy.r_dong > 0 ? 0.05 * r_gu + 0.95 * dy.r_dong : r_gu;
            if (t >= XUE_QI) {
                if (dy.r_man <= 0) dy.r_man = dy.r_dong;
                else dy.r_man += 0.002 * (dy.r_dong - dy.r_man);
            }
            if (dy.r_man > 0 && t >= XUE_QI) {
                double zeng = (dy.r_dong - dy.r_man) / dy.r_man;
                if (zeng > DIAN_ZU_ZENG) {
                    dy.zu_ji++;
                    if (dy.zu_ji >= 10 && !dy.zu_guai) {
                        dy.zu_guai = 1;
                        shi_jian_xing("ALARM|%s|t=%d|leixing=DIANYU|dao=u_bat|label=DIANCHI_NEIZU|zhi=%.4f\n",
                                      wo_jiedian, t, dy.r_dong);
                    }
                } else {
                    dy.zu_ji = 0;
                    if (dy.zu_guai && zeng < 0.06) {
                        dy.zu_guai = 0;
                        shi_jian_xing("RECOVER|%s|t=%d|leixing=DIANYU|dao=u_bat|label=DIANCHI_NEIZU\n",
                                      wo_jiedian, t);
                    }
                }
            }
        }
    }
    if (t >= XUE_QI && dy.r_ji <= 0 && dy.r_dong > 0) dy.r_ji = dy.r_dong;
    if (dy.shang_shi == 0 && zhi[4] > 60.0) {
        if (zhi[2] < 0.2) {
            dy.chong_wu_ji++;
            if (dy.chong_wu_ji >= CHONG_WU && !dy.chong_wu_guai) {
                dy.chong_wu_guai = 1;
                shi_jian_xing("ALARM|%s|t=%d|leixing=DIANYU|dao=i_bat|label=CHONGDIAN_SHIXIAO|zhi=%.3f\n",
                              wo_jiedian, t, zhi[2]);
            }
        } else {
            dy.chong_wu_ji = 0;
            if (dy.chong_wu_guai) {
                dy.chong_wu_guai = 0;
                shi_jian_xing("RECOVER|%s|t=%d|leixing=DIANYU|dao=i_bat|label=CHONGDIAN_SHIXIAO\n",
                              wo_jiedian, t);
            }
        }
    } else {
        dy.chong_wu_ji = 0;
    }
    if (t >= XUE_QI && dy.shang_shi != 1) {
        if (zhi[5] > WEN_XIAN) {
            dy.wen_ji++;
            if (dy.wen_ji >= 20 && !dy.wen_guai) {
                dy.wen_guai = 1;
                shi_jian_xing("ALARM|%s|t=%d|leixing=DIANYU|dao=w_pcu|label=GUOWEN|zhi=%.3f\n",
                              wo_jiedian, t, zhi[5]);
            }
        } else {
            if (zhi[5] < WEN_XIAN - 8.0) dy.wen_ji = 0;
            if (dy.wen_guai && zhi[5] < WEN_XIAN - 4.0) {
                dy.wen_guai = 0;
                shi_jian_xing("RECOVER|%s|t=%d|leixing=DIANYU|dao=w_pcu|label=GUOWEN\n", wo_jiedian, t);
            }
        }
    }
    if (t >= XUE_QI && dy.shang_shi != 1) {
        if (zhi[0] < 26.0) {
            dy.muxian_ji++;
            if (dy.muxian_ji >= 5 && !dy.muxian_guai) {
                dy.muxian_guai = 1;
                shi_jian_xing("ALARM|%s|t=%d|leixing=DIANYU|dao=u_bus|label=MUXIAN_DIELUO|zhi=%.3f\n",
                              wo_jiedian, t, zhi[0]);
            }
        } else {
            dy.muxian_ji = 0;
            if (dy.muxian_guai && zhi[0] > 26.8) {
                dy.muxian_ji_hui++;
                if (dy.muxian_ji_hui >= 20) {
                    dy.muxian_guai = 0;
                    dy.muxian_ji_hui = 0;
                    shi_jian_xing("RECOVER|%s|t=%d|leixing=DIANYU|dao=u_bus|label=MUXIAN_DIELUO\n",
                                  wo_jiedian, t);
                }
            } else {
                dy.muxian_ji_hui = 0;
            }
        }
    }
    if (dy.soc < 0.18 && !dy.guo_dian_guai) {
        dy.guo_dian_guai = 1;
        shi_jian_xing("ALARM|%s|t=%d|leixing=DIANYU|dao=soc|label=GUODIAN|zhi=%.3f\n",
                      wo_jiedian, t, dy.soc);
    }
    if (dy.guo_dian_guai && dy.soc > 0.25) {
        dy.guo_dian_guai = 0;
        shi_jian_xing("RECOVER|%s|t=%d|leixing=DIANYU|dao=soc|label=GUODIAN\n", wo_jiedian, t);
    }
    if (dy.soc < dy.dod_ben || dy.dod_ben <= 0.0) dy.dod_ben = 1.0 - dy.soc;
    if (dy.shang_shi == 0 && zhi[4] > dy.ben_feng) dy.ben_feng = zhi[4];
}

struct zhu_ru {
    int bus_kai, bus_he;
    int zu_t;
    int chong_kai, chong_he;
    int wen_kai, wen_he;
    int guang_kai;
    int seu_t;
};

static void mo_xing(int t, const struct zhu_ru *z, double zhi[DAO_SHU])
{
    int gui = t % ZHOU_QI;
    int zhaoshe = gui < DI_YING_KAI || gui >= DI_YING_HE;
    double p_pv = 0.0;
    if (zhaoshe) {
        double wei = gui < DI_YING_KAI ? (gui + (ZHOU_QI - DI_YING_HE)) / (double)(ZHOU_QI - DI_YING_KAI)
                                       : (gui - DI_YING_HE) / (double)(ZHOU_QI - DI_YING_HE);
        double xiang = M_PI * (0.458 + wei * 0.542);
        if (gui >= DI_YING_HE) xiang = M_PI * wei * 0.458;
        p_pv = P0 * (0.72 + 0.28 * sin(xiang));
        if (gui >= DI_YING_HE && gui < DI_YING_HE + 5)
            p_pv *= (gui - DI_YING_HE + 1) / 6.0;
    }
    double p_fu = FU_ZAI * (1.0 + 0.08 * sin(2.0 * M_PI * gui / ZHOU_QI)) + gauss(0, 0.4);
    double r = R_JI * (1.0 + R_ZENG * dy.xunhuan);
    if (z->zu_t > 0 && t >= z->zu_t) r *= 1.6;
    double i_jing;
    if (zhaoshe && p_pv > 0.0) {
        i_jing = (p_pv * 0.95 - p_fu) / 26.0;
        if (dy.soc > 0.99) i_jing = -p_fu / 26.0;
        if (z->chong_kai > 0 && t >= z->chong_kai && t < z->chong_he) i_jing = 0.0;
    } else {
        i_jing = -p_fu / 26.0;
        if (gui >= DI_YING_KAI && gui < DI_YING_KAI + 4)
            i_jing *= (gui - DI_YING_KAI + 1) / 5.0;
    }
    double u_bat = U0 + U_FU * dy.soc + i_jing * r + gauss(0, 0.02);
    double u_bus;
    if (zhaoshe && p_pv > 0.0) u_bus = 28.3 + gauss(0, 0.05);
    else u_bus = u_bat + 1.4 + gauss(0, 0.05);
    if (z->bus_kai > 0 && t >= z->bus_kai && t < z->bus_he) u_bus -= 6.0;
    if (z->seu_t > 0 && t == z->seu_t) {
        p_pv += 60.0;
        u_bus += 3.0;
    }
    if (z->guang_kai > 0 && t >= z->guang_kai) {
        double bi = (double)(t - z->guang_kai) / 150.0;
        if (bi > 1.0) bi = 1.0;
        p_pv *= (1.0 - 0.35 * bi);
    }
    double w_pcu = 15.0 + 8.0 * sin(2.0 * M_PI * gui / ZHOU_QI) + fmax(0.0, i_jing) * 0.12 + gauss(0, 0.15);
    if (z->wen_kai > 0 && t >= z->wen_kai && t < z->wen_he) w_pcu += 35.0;

    dy.soc += i_jing * u_bat / 3600.0 / E_RONG;
    if (dy.soc > 1.0) dy.soc = 1.0;
    if (dy.soc < 0.0) dy.soc = 0.0;

    zhi[0] = u_bus;
    zhi[1] = u_bat;
    zhi[2] = i_jing;
    zhi[3] = p_fu / 26.0;
    zhi[4] = p_pv;
    zhi[5] = w_pcu;
}

static void biao_ji_shu(int t, FILE *mu)
{
    for (int k = 0; (DI_YING_KAI + k * ZHOU_QI) < t; k++) {
        fprintf(mu, "BIAOJI|leixing=GUODU|kaishi=%d|jieshu=%d\n",
                DI_YING_KAI + k * ZHOU_QI, DI_YING_KAI + k * ZHOU_QI + GUODU_SHU);
        fprintf(mu, "BIAOJI|leixing=GUODU|kaishi=%d|jieshu=%d\n",
                DI_YING_HE + k * ZHOU_QI, DI_YING_HE + k * ZHOU_QI + GUODU_SHU);
    }
}

static void zhu_ru_mo_ren(struct zhu_ru *z)
{
    memset(z, 0, sizeof(*z));
    z->bus_kai = 980; z->bus_he = 1040;
    z->zu_t = 1350;
    z->chong_kai = 1100; z->chong_he = 1180;
    z->wen_kai = 1200; z->wen_he = 1300;
    z->guang_kai = 1150;
    z->seu_t = 700;
}

struct biao_ji {
    const char *leixing;
    int kaishi, jieshu;
};

static int bao_t_zhao(const char *hang, const char *qian, const char *ming)
{
    size_t c_q = strlen(qian), c_m = strlen(ming);
    if (strncmp(hang, qian, c_q) != 0) return 0;
    const char *w = strstr(hang + c_q, ming);
    if (!w) return 0;
    char hou = w[c_m];
    return hou == '|' || hou == '\n' || hou == 0;
}

static int zice_main(void)
{
    srand(20260912);
    dy_chu_shi();
    dy.jia_za = 1;
    shi_chu = tmpfile();
    struct zhu_ru z;
    zhu_ru_mo_ren(&z);
    struct biao_ji biao[] = {
        {"SEU", 700, 700},
        {"MUXIAN_DIELUO", 980, 1040},
        {"CHONGDIAN_SHIXIAO", 1100, 1180},
        {"GUOWEN", 1200, 1300},
        {"DIANCHI_NEIZU", 1350, 2000},
        {"GUANGFU_SHUAIJIAN", 1150, 2000},
    };
    double soh_0 = 100.0, soh_1 = 100.0;
    double zhi[DAO_SHU];
    for (int t = 0; t < 2000; t++) {
        mo_xing(t, &z, zhi);
        if (t == 800) soh_0 = soh_zhi();
        tui_yi_bang(t, zhi);
        if (t % 50 == 0) bao_gao_yi_hang(t, zhi, shi_chu);
    }
    soh_1 = soh_zhi();
    fflush(shi_chu);
    rewind(shi_chu);

    int bao_t[6], hui_t[6], seu_shu = 0;
    for (int m = 0; m < 6; m++) { bao_t[m] = -1; hui_t[m] = -1; }
    char hang[256];
    while (fgets(hang, sizeof(hang), shi_chu)) {
        for (int m = 0; m < 6; m++) {
            if (bao_t[m] < 0 && bao_t_zhao(hang, "ALARM|", biao[m].leixing)) {
                int t = atoi(strstr(hang, "|t=") + 3);
                if (t >= biao[m].kaishi - 2 && t <= biao[m].jieshu + 80) bao_t[m] = t;
            }
            if (hui_t[m] < 0 && bao_t[m] >= 0 && bao_t_zhao(hang, "RECOVER|", biao[m].leixing)) {
                int t = atoi(strstr(hang, "|t=") + 3);
                if (t >= biao[m].jieshu) hui_t[m] = t;
            }
        }
        if (strncmp(hang, "SEU|", 4) == 0) seu_shu++;
    }
    int huai = 0;
    int xu_hui[] = {0, 1, 1, 1, 0, 0};
    for (int m = 0; m < 6; m++) {
        int zhao = m == 0 ? seu_shu >= 1 : bao_t[m] >= 0;
        int hui_ok = hui_t[m] > 0 || !xu_hui[m];
        printf("ZICE %s leixing=%s fa_xian=%s(t=%d) hui_fu=%s(t=%d)\n",
               (zhao && hui_ok) ? "PASS" : "FAIL", biao[m].leixing,
               zhao ? "shi" : "fou", bao_t[m], hui_t[m] > 0 ? "shi" : "fou", hui_t[m]);
        if (!zhao || !hui_ok) huai = 1;
    }
    printf("ZICE SEU shu_liang=%d (qi_wang=1)\n", seu_shu);
    if (seu_shu != 1) huai = 1;
    printf("ZICE guodu_wu_bao=%d (qi_wang=0)\n", dy.guodu_bao);
    if (dy.guodu_bao != 0) huai = 1;
    printf("ZICE xunhuan=%d dod=%.2f soh %.1f -> %.1f rul=%.0f\n",
           dy.xunhuan, dy.dod_ben, soh_0, soh_1, rul_zhi());
    if (dy.xunhuan < 3 || dy.dod_ben < 0.05 || dy.dod_ben > 0.5) huai = 1;
    if (soh_1 > soh_0 - 5.0 || soh_1 < 40.0) huai = 1;
    if (rul_zhi() <= 0) huai = 1;
    fclose(shi_chu);
    if (!huai) {
        printf("ZICE PASS: liu lei gu zhang quan bu fa xian, guodu gan jing, SEU dan ci, SOH/RUL you xiao\n");
        return 0;
    }
    printf("ZICE FAIL\n");
    return 1;
}

static int moxing_main(int ticks)
{
    srand(20260912);
    dy_chu_shi();
    dy.jia_za = 1;
    shi_chu = stdout;
    struct zhu_ru z;
    zhu_ru_mo_ren(&z);
    struct biao_ji biao[] = {
        {"SEU", 700, 700},
        {"MUXIAN_DIELUO", 980, 1040},
        {"CHONGDIAN_SHIXIAO", 1100, 1180},
        {"GUOWEN", 1200, 1300},
        {"DIANCHI_NEIZU", 1350, ticks},
        {"GUANGFU_SHUAIJIAN", 1150, ticks},
    };
    for (int m = 0; m < 6; m++)
        fprintf(stderr, "BIAOJI|leixing=%s|kaishi=%d|jieshu=%d\n", biao[m].leixing, biao[m].kaishi, biao[m].jieshu);
    biao_ji_shu(ticks, stderr);
    double zhi[DAO_SHU];
    for (int t = 0; t < ticks; t++) {
        mo_xing(t, &z, zhi);
        for (int c = 0; c < DAO_SHU; c++)
            printf("%.4f%c", zhi[c], c == DAO_SHU - 1 ? '\n' : ' ');
    }
    return 0;
}

static int shuru_main(void)
{
    srand(20260912);
    dy_chu_shi();
    dy.wai_shu = 1;
    dy.jia_za = 0;
    shi_chu = stdout;
    char hang[512];
    int t = 0;
    double zhi[DAO_SHU];
    while (fgets(hang, sizeof(hang), stdin)) {
        if (sscanf(hang, "%lf %lf %lf %lf %lf %lf",
                   &zhi[0], &zhi[1], &zhi[2], &zhi[3], &zhi[4], &zhi[5]) != DAO_SHU) continue;
        tui_yi_bang(t, zhi);
        if (t % 50 == 0) bao_gao_yi_hang(t, zhi, stdout);
        t++;
    }
    printf("ZUIZHOU|soh=%.1f|rul=%.0f|xunhuan=%d|dod=%.2f\n",
           soh_zhi(), rul_zhi(), dy.xunhuan, dy.dod_ben);
    return 0;
}

int main(int jianshu, char *canshu[])
{
    if (jianshu > 1 && strcmp(canshu[1], "--zice") == 0) return zice_main();
    if (jianshu > 1 && strcmp(canshu[1], "--moxing") == 0)
        return moxing_main(jianshu > 2 ? atoi(canshu[2]) : 2000);
    if (jianshu > 1 && strcmp(canshu[1], "--shuru") == 0) return shuru_main();
    char jiedian_guo[64] = "weixing1";
    if (du_zhi("jiedian", jiedian_guo, sizeof(jiedian_guo)) != 0) strcpy(jiedian_guo, "weixing1");
    wo_jiedian = jiedian_guo;
    if (jianshu > 1) wo_jiedian = canshu[1];
    srand(time(NULL) + (int)wo_jiedian[0]);
    dy_chu_shi();
    dy.jia_za = 1;
    shi_chu = stdout;
    struct zhu_ru z;
    zhu_ru_mo_ren(&z);
    memset(&z, 0, sizeof(z));
    double zhi[DAO_SHU];
    printf("电源系统健康管理启动 节点=%s 通道=%d\n", wo_jiedian, DAO_SHU);
    for (int t = 0;; t++) {
        mo_xing(t, &z, zhi);
        tui_yi_bang(t, zhi);
        if (t % 50 == 0) bao_gao_yi_hang(t, zhi, stdout);
        usleep(20000);
    }
    return 0;
}
