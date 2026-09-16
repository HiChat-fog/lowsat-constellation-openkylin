#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "zhushou.h"

static void ce_jie_wen_zhengchang(void)
{
    char duc[64];
    int wei = jie_wen(duc, sizeof(duc), 0, "{\"a\":%d,", 7);
    wei = jie_wen(duc, sizeof(duc), wei, "\"b\":\"%s\"}", "ceshi");
    assert(wei == (int)strlen(duc));
    assert(strcmp(duc, "{\"a\":7,\"b\":\"ceshi\"}") == 0);
}

static void ce_jie_wen_yuejie(void)
{
    char duc[16];
    int wei = 0;
    for (int i = 0; i < 100; i++)
        wei = jie_wen(duc, sizeof(duc), wei, "%08d", i);
    assert(wei == sizeof(duc) - 1);
    assert(strlen(duc) == 15);
    char jian[64];
    memset(jian, 'x', sizeof(jian));
    wei = jie_wen(jian, sizeof(jian), sizeof(jian) - 1, "%s", "yue jie le");
    assert(wei == sizeof(jian) - 1);
    long bao_cun = 0;
    for (unsigned long i = 0; i < sizeof(jian); i++) bao_cun += jian[i];
    assert(bao_cun == (long)sizeof(jian) * 'x');
}

static void ce_bao_zhuangtai(void)
{
    struct baojing b = {0, 0};
    assert(bao_zhuangtai(&b, 1, 2) == 0);
    assert(bao_zhuangtai(&b, 1, 2) == 1);
    assert(bao_zhuangtai(&b, 1, 2) == 0);
    assert(bao_zhuangtai(&b, 0, 2) == -1);
    assert(bao_zhuangtai(&b, 0, 2) == 0);
    assert(bao_zhuangtai(&b, 1, 3) == 0);
    assert(bao_zhuangtai(&b, 0, 3) == 0);
    assert(bao_zhuangtai(&b, 1, 3) == 0);
    assert(bao_zhuangtai(&b, 1, 3) == 0);
    assert(bao_zhuangtai(&b, 1, 3) == 1);
    struct baojing c = {0, 0};
    assert(bao_zhuangtai(&c, 1, 1) == 1);
    assert(bao_zhuangtai(&c, 0, 1) == -1);
}

int main(void)
{
    ce_jie_wen_zhengchang();
    ce_jie_wen_yuejie();
    ce_bao_zhuangtai();
    printf("C dan yuan ce shi: 3/3 tong guo\n");
    return 0;
}
