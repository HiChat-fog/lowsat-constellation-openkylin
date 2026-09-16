#ifndef PEIZHI_H
#define PEIZHI_H

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static const char *peizhi_lu = "/etc/weixing/weixing.conf";

static int du_zhi(const char *key, char *guo, int guo_len)
{
    FILE *f = fopen(peizhi_lu, "r");
    if (!f) return -1;
    char hang[512];
    int zhao = -1;
    while (fgets(hang, sizeof(hang), f)) {
        char *deng = strchr(hang, '=');
        if (!deng) continue;
        *deng = 0;
        char *ming = hang;
        char *zhi = deng + 1;
        while (*ming == ' ' || *ming == '\t') ming++;
        char *p = ming + strlen(ming) - 1;
        while (p >= ming && (*p == ' ' || *p == '\t' || *p == '\n')) *p-- = 0;
        while (*zhi == ' ' || *zhi == '\t') zhi++;
        p = zhi + strlen(zhi) - 1;
        while (p >= zhi && (*p == ' ' || *p == '\t' || *p == '\n')) *p-- = 0;
        if (strcmp(ming, key) == 0) {
            snprintf(guo, guo_len, "%s", zhi);
            zhao = 0;
            break;
        }
    }
    fclose(f);
    return zhao;
}

static int __attribute__((unused)) du_zhi_int(const char *key, int mo_ren)
{
    char guo[128];
    if (du_zhi(key, guo, sizeof(guo)) == 0)
        return atoi(guo);
    return mo_ren;
}

static double __attribute__((unused)) du_zhi_shuang(const char *key, double mo_ren)
{
    char guo[128];
    if (du_zhi(key, guo, sizeof(guo)) == 0)
        return atof(guo);
    return mo_ren;
}

#endif