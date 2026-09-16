#ifndef ZHUSHOU_H
#define ZHUSHOU_H

#include <stdio.h>
#include <stdarg.h>

static int jie_wen(char *duc, int da, int wei, const char *geshi, ...)
{
    va_list c;
    int n;
    if (wei >= da - 1) return wei;
    va_start(c, geshi);
    n = vsnprintf(duc + wei, da - wei, geshi, c);
    va_end(c);
    if (n < 0) return wei;
    if (n >= da - wei) return da - 1;
    return wei + n;
}

struct baojing { int lianxu; int jihuo; };

static int bao_zhuangtai(struct baojing *b, int tiaojian, int n)
{
    if (tiaojian) {
        b->lianxu++;
        if (!b->jihuo && b->lianxu >= n) { b->jihuo = 1; return 1; }
    } else {
        b->lianxu = 0;
        if (b->jihuo) { b->jihuo = 0; return -1; }
    }
    return 0;
}

#endif
