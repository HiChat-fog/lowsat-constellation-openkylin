#ifndef JIANCE_YINQING_H
#define JIANCE_YINQING_H

#include <math.h>
#include <stdio.h>

#define ZUI_DA_DAO 64
#define CHUANG 30
#define WU_MEN (2 * CHUANG)
#define BAO_ZHI 3.5
#define TB_LIAN 2
#define BI_LIAN 5
#define HUI_ZHI 2.0
#define BI_BAO 2.5
#define BI_JING 1.8
#define PIAO_BEI 3.0
#define PIAO_LIAN 8
#define AN_JING_XU 20

static const char *lei_ming[ZUI_DA_DAO + 1] = {"TB", "PIAO_YI", "FANG_CHA", "KA_SI", "?"};

static void (*yin_qing_gua_zhong)(const char *dongzuo, int t_hao, const char *dao_ming, double zhi) = 0;

struct dao_tai {
    double chuang[CHUANG];
    double fang_man;
    double feng;
    double s_man;
    double suo_zhong;
    double suo_mad;
    double man_pian;
    int chu_shi;
    int guai;
    int an_jing;
    int leixing_ma;
    int piao_lian;
    int piao_zheng;
    int lian_tb;
    int lian_bi;
    int jing_bai;
    int yang_ben;
    double bao_duo;
};

static void pai_xu(double *a, int n)
{
    for (int i = 1; i < n; i++) {
        double yao = a[i];
        int j = i - 1;
        for (; j >= 0 && a[j] > yao; j--) a[j + 1] = a[j];
        a[j + 1] = yao;
    }
}

static double jie_zhong_wei(double *a, int n)
{
    pai_xu(a, n);
    return (a[n / 2 - 1] + a[n / 2]) / 2;
}

static double jie_mad(const double *chuang, double *zhong_out)
{
    double pai[CHUANG], jue[CHUANG];
    for (int i = 0; i < CHUANG; i++) pai[i] = chuang[i];
    double zw = jie_zhong_wei(pai, CHUANG);
    for (int i = 0; i < CHUANG; i++) jue[i] = fabs(pai[i] - zw);
    *zhong_out = zw;
    return jie_zhong_wei(jue, CHUANG);
}

static double jie_xie_lv(const struct dao_tai *t, double xin)
{
    double qian[CHUANG / 2], hou[CHUANG / 2];
    for (int i = 0; i < CHUANG / 2; i++) {
        qian[i] = t->chuang[i];
        hou[i] = t->chuang[CHUANG / 2 + i];
    }
    hou[CHUANG / 2 - 1] = xin;
    double q = jie_zhong_wei(qian, CHUANG / 2);
    double h = jie_zhong_wei(hou, CHUANG / 2);
    return (h - q) / (CHUANG / 2);
}

static void tui_yi_dao(struct dao_tai *t, double xin, int t_hao, const char *jiedian, const char *dao_ming_chen)
{
    double zw = 0, mad = 0, kuai = 0, med_slope = 0;
    if (t->yang_ben >= CHUANG) {
        mad = jie_mad(t->chuang, &zw);
        kuai = mad * 1.4826;
        med_slope = jie_xie_lv(t, xin);
    }
    if (!t->chu_shi && t->yang_ben >= CHUANG) {
        t->fang_man = kuai;
        t->feng = kuai;
        t->s_man = fabs(med_slope);
        t->suo_zhong = zw;
        t->man_pian = fabs(xin - zw);
        t->chu_shi = 1;
    }
    double can_kao = t->fang_man > 1e-9 ? t->fang_man : 1e-9;
    double chi_du = fmax(kuai, can_kao);
    double z_kuai = (xin - zw) / chi_du;
    double bei = kuai > 1e-9 ? kuai / fmax(t->feng, 1e-9) : 0.0;
    int ka_si = (kuai < 1e-9 && can_kao > 0.3 && fabs(xin - zw) < 1e-9);
    int tb_tiao = fabs(z_kuai) > BAO_ZHI;
    int bi_tiao = bei > BI_BAO;
    if (!t->guai) {
        if (tb_tiao) t->lian_tb++;
        else t->lian_tb = 0;
        if (bi_tiao) t->lian_bi++;
        else t->lian_bi = 0;
    }

    if (t->s_man > 1e-12 && fabs(med_slope) > PIAO_BEI * t->s_man) {
        int zheng = med_slope > 0;
        if (t->piao_lian > 0 && t->piao_zheng != zheng) t->piao_lian = 0;
        t->piao_lian++;
        t->piao_zheng = zheng;
    } else {
        t->piao_lian = 0;
    }

    if (t->guai) {
        int jing = 0;
        if (t->leixing_ma == 1) {
            double xie_bi = t->s_man > 1e-12 ? fabs(med_slope) / t->s_man : 0.0;
            if (xie_bi > PIAO_BEI && (xie_bi > PIAO_BEI + 3.0 || t->piao_lian >= PIAO_LIAN) && xie_bi >= bei) {
                t->leixing_ma = 2;
                printf("GENG_LEI|%s|t=%d|%s|leixing=PIAO_YI\n", jiedian, t_hao, dao_ming_chen);
            } else if (bei > BI_BAO && fabs(zw - t->suo_zhong) < 2.0 * t->suo_mad) {
                t->leixing_ma = 3;
                printf("GENG_LEI|%s|t=%d|%s|leixing=FANG_CHA\n", jiedian, t_hao, dao_ming_chen);
            }
            jing = fabs(xin - t->suo_zhong) < fmax(fmax(HUI_ZHI * t->suo_mad, 3.0 * t->man_pian),
                                                   4.0 * chi_du);
        } else if (t->leixing_ma == 2) {
            jing = fabs(med_slope) <= PIAO_BEI * t->s_man
                   && fabs(xin - t->suo_zhong) < fmax(HUI_ZHI * t->suo_mad, 3.0 * t->man_pian);
        } else if (t->leixing_ma == 3) {
            jing = bei < BI_JING;
        } else {
            jing = !ka_si;
        }
        if (jing) {
            t->an_jing++;
            if (t->an_jing >= AN_JING_XU) {
                t->guai = 0;
                t->jing_bai = 0;
                printf("RECOVER|%s|t=%d|%s|leixing=%s|zhi=%.2f\n",
                       jiedian, t_hao, dao_ming_chen, lei_ming[t->leixing_ma - 1], xin);
                if (yin_qing_gua_zhong)
                    yin_qing_gua_zhong("RECOVER", t_hao, dao_ming_chen, xin);
            }
        } else {
            t->an_jing = 0;
        }
    } else if (t_hao >= WU_MEN && t->jing_bai >= CHUANG * (1 + (int)fmin(t->bao_duo, 9.0))) {
        const char *bao = NULL;
        int bao_ma = 0;
        if (ka_si) {
            bao = "KA_SI"; bao_ma = 4;
        } else if (bi_tiao && t->lian_bi >= BI_LIAN
                   && fabs(zw - t->suo_zhong) < 2.0 * t->suo_mad) {
            bao = "FANG_CHA"; bao_ma = 3;
        } else if (tb_tiao && t->lian_tb >= TB_LIAN) {
            bao = "TB"; bao_ma = 1;
        } else if (t->piao_lian >= PIAO_LIAN) {
            bao = "PIAO_YI"; bao_ma = 2;
        }
        if (bao) {
            t->guai = 1;
            t->an_jing = 0;
            t->jing_bai = 0;
            t->bao_duo += 1.0;
            t->lian_tb = 0;
            t->lian_bi = 0;
            t->leixing_ma = bao_ma;
            t->suo_zhong = zw;
            t->suo_mad = fmax(kuai, can_kao);
            printf("ALARM|%s|t=%d|%s|leixing=%s|z=%.1f|zhi=%.2f\n",
                   jiedian, t_hao, dao_ming_chen, bao, z_kuai, xin);
            if (yin_qing_gua_zhong)
                yin_qing_gua_zhong("ALARM", t_hao, dao_ming_chen, xin);
        }
    }

    if (!t->guai) {
        t->jing_bai++;
        t->bao_duo *= 0.999;
    }

    if (!t->guai && !ka_si && t->yang_ben >= CHUANG && kuai > 1e-9) {
        if (t->piao_lian == 0) {
            if (fabs(med_slope) > t->s_man) t->s_man = fabs(med_slope);
            else t->s_man *= 0.998;
        }
        if (kuai > t->feng) t->feng = kuai;
        else t->feng *= 0.998;
        t->fang_man = 0.98 * t->fang_man + 0.02 * kuai;
        t->suo_zhong += 0.005 * (xin - t->suo_zhong);
        double pian_now = fabs(xin - t->suo_zhong);
        if (pian_now > t->man_pian) t->man_pian = pian_now;
        else t->man_pian *= 0.999;
    }

    for (int k = 0; k < CHUANG - 1; k++) t->chuang[k] = t->chuang[k + 1];
    t->chuang[CHUANG - 1] = xin;
    t->yang_ben++;
}

#endif
