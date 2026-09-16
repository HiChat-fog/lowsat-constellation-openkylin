#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <stdarg.h>
#include <signal.h>
#include <time.h>
#include <sqlite3.h>
#include <sys/stat.h>
#include "peizhi.h"
#include "zhushou.h"
#include "agent.skel.h"
#include "mingling_tab.h"

#ifndef BAN_BEN
#define BAN_BEN "dev"
#endif

static volatile int jixu = 1;
static volatile int chong_du = 0;
static void tingzhi(int hao) { (void)hao; jixu = 0; }
static void chong_du_peizhi(int hao) { (void)hao; chong_du = 1; }
static sqlite3 *ku;
static sqlite3_stmt *charu;
static sqlite3_stmt *shijian_charu;
static FILE *shijian_wen;

static void lun_zhuan(int fd, long shang_xian)
{
    struct stat st;
    if (fstat(fd, &st) != 0 || st.st_size <= shang_xian) return;
    long bao = 65536;
    if (st.st_size < bao) bao = st.st_size;
    char *weiba = malloc(bao);
    if (!weiba) return;
    if (lseek(fd, st.st_size - bao, SEEK_SET) < 0) { free(weiba); return; }
    long du = (long)read(fd, weiba, bao);
    if (ftruncate(fd, 0) == 0) {
        lseek(fd, 0, SEEK_SET);
        if (du > 0) write(fd, weiba, du);
    }
    free(weiba);
}

static void cun_shijian(const char *jiedian, const char *leixing, const char *neirong)
{
    fprintf(stderr, "%s|%s|%s\n", leixing, jiedian, neirong);
    if (shijian_wen) {
        lun_zhuan(fileno(shijian_wen), 1 << 20);
        fprintf(shijian_wen, "%s|%s|%s\n", leixing, jiedian, neirong);
        fflush(shijian_wen);
    }
    if (ku && shijian_charu) {
        sqlite3_reset(shijian_charu);
        sqlite3_clear_bindings(shijian_charu);
        sqlite3_bind_text(shijian_charu, 1, jiedian, -1, SQLITE_STATIC);
        sqlite3_bind_text(shijian_charu, 2, leixing, -1, SQLITE_STATIC);
        sqlite3_bind_text(shijian_charu, 3, neirong, -1, SQLITE_STATIC);
        sqlite3_step(shijian_charu);
    }
}

static long du_ziji_rss(void)
{
    FILE *f = fopen("/proc/self/status", "r");
    if (!f) return -1;
    char hang[256];
    long kb = -1;
    while (fgets(hang, sizeof(hang), f)) {
        if (sscanf(hang, "VmRSS: %ld", &kb) == 1) break;
    }
    fclose(f);
    return kb;
}

static void bao_zijian(const char *jiedian)
{
    long kb = du_ziji_rss();
    if (kb < 0) return;
    char neirong[128];
    snprintf(neirong, sizeof(neirong), "ziji neicun %ldKB", kb);
    cun_shijian(jiedian, "ZIJIAN", neirong);
}

static void qing_ku(void)
{
    if (!ku) return;
    sqlite3_exec(ku, "DELETE FROM guance WHERE id <= (SELECT IFNULL(MAX(id),0) FROM guance) - 20000", 0, 0, 0);
    sqlite3_exec(ku, "DELETE FROM shijian_biao WHERE id <= (SELECT IFNULL(MAX(id),0) FROM shijian_biao) - 5000", 0, 0, 0);
}

static int hai_zai(int pid)
{
    char lu[32];
    snprintf(lu, sizeof(lu), "/proc/%d", pid);
    return access(lu, F_OK) == 0;
}

static void qing_ming(const char *ru, char *chu, int da)
{
    int i = 0;
    for (; i < da - 1 && ru[i]; i++) {
        unsigned char c = (unsigned char)ru[i];
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
            || c == '.' || c == '-' || c == '_' || c == ' ')
            chu[i] = (char)c;
        else
            chu[i] = '_';
    }
    chu[i] = 0;
}

struct jilu { __u32 id; __u64 ci; };
struct paiming { __u32 pid; char ming[16]; __u64 haoshi; };
struct paiming_zeng { __u32 pid; char ming[16]; __u64 zeng; };
struct mingl { char ming[16]; __u64 ci; };

static struct paiming_zeng shangci_suan[256];
static int shangci_suan_ge = 0;

static struct baojing bao_cpu, bao_mem, bao_sys, bao_suanli;
static __u64 shangci_total = 0;
static __u64 shangci_qiehuan = 0;

static int bijiao_ci(const void *a, const void *b)
{
    const struct jilu *x = a, *y = b;
    return y->ci > x->ci ? 1 : (y->ci < x->ci ? -1 : 0);
}
static int bijiao_zeng(const void *a, const void *b)
{
    const struct paiming_zeng *x = a, *y = b;
    return y->zeng > x->zeng ? 1 : (y->zeng < x->zeng ? -1 : 0);
}
static int bijiao_qiehuan(const void *a, const void *b)
{
    const struct mingl *x = a, *y = b;
    return y->ci > x->ci ? 1 : (y->ci < x->ci ? -1 : 0);
}

static double du_cpu(void)
{
    FILE *f = fopen("/proc/stat", "r");
    if (!f) return 0;
    char hang[512];
    double zong = 0, kongxian = 0;
    while (fgets(hang, sizeof(hang), f)) {
        if (strncmp(hang, "cpu ", 4) == 0) {
            long a[8]; int ge = sscanf(hang + 4, "%ld %ld %ld %ld %ld %ld %ld %ld",
                                       &a[0], &a[1], &a[2], &a[3], &a[4], &a[5], &a[6], &a[7]);
            for (int i = 0; i < ge; i++) zong += a[i];
            kongxian = a[3] + a[4];
            break;
        }
    }
    fclose(f);
    static double sz = 0, sk = 0;
    double zhan = 0;
    if (sz > 0 && zong > sz) zhan = 100.0 * (zong - sz - (kongxian - sk)) / (zong - sz);
    sz = zong; sk = kongxian;
    return zhan < 0 ? 0 : zhan;
}

static long du_mem(void)
{
    FILE *f = fopen("/proc/meminfo", "r");
    if (!f) return -1;
    char hang[512];
    long zong = 0, keyong = 0;
    while (fgets(hang, sizeof(hang), f)) {
        if (sscanf(hang, "MemTotal: %ld", &zong) == 1) continue;
        if (sscanf(hang, "MemAvailable: %ld", &keyong) == 1) break;
    }
    fclose(f);
    if (zong <= 0) return -1;
    return 100 * (zong - keyong) / zong;
}

static double sys_yuzhi = 150.0;
static double cpu_yuzhi = 85.0;
static double mem_yuzhi = 85.0;
static double suanli_yuzhi = 50.0;
static int lu_ku_bai = 0;
static int shangci_bai = 0;
static int lin_kong = 0;

static void baogao(struct agent_bpf *qiti, const char *jiedian, int lunci, int zhoudao)
{
    lun_zhuan(STDOUT_FILENO, 3 << 20);
    time_t ke = time(NULL);
    struct tm *xian = localtime(&ke);
    double cpu = du_cpu();
    long mem = du_mem();

    __u32 jian0 = 0; __u64 qiehuan = 0;
    bpf_map__lookup_elem(qiti->maps.shijian_map, &jian0, 4, &qiehuan, 8, 0);
    __u32 jian1 = 1; __u64 zhixing = 0;
    bpf_map__lookup_elem(qiti->maps.shijian_map, &jian1, 4, &zhixing, 8, 0);
    __u32 jian2 = 2; __u64 fanzhi = 0;
    bpf_map__lookup_elem(qiti->maps.shijian_map, &jian2, 4, &fanzhi, 8, 0);
    __u32 jian3 = 3; __u64 diao_shu = 0;
    bpf_map__lookup_elem(qiti->maps.diao_map, &jian3, 4, &diao_shu, 8, 0);
    if (diao_shu > 0 && lunci % 20 == 0) {
        char neirong[128];
        snprintf(neirong, sizeof(neirong), "BPF biao man, diu qi %llu ci tong ji", (unsigned long long)diao_shu);
        cun_shijian(jiedian, "XITONG", neirong);
    }

    struct jilu *sys = malloc(sizeof(struct jilu) * 512);
    struct paiming *suan = malloc(sizeof(struct paiming) * 256);
    struct paiming_zeng *zeng_l = malloc(sizeof(struct paiming_zeng) * 256);
    struct mingl *qih = malloc(sizeof(struct mingl) * 256);
    if (!sys || !suan || !zeng_l || !qih) {
        free(sys); free(suan); free(zeng_l); free(qih);
        return;
    }
    int sys_ge = 0;
    __u32 jian = 0; __u64 zhi = 0;
    while (bpf_map__get_next_key(qiti->maps.cishu_map, &jian, &jian, 4) == 0 && sys_ge < 512) {
        if (bpf_map__lookup_elem(qiti->maps.cishu_map, &jian, 4, &zhi, 8, 0) == 0 && zhi > 0) {
            sys[sys_ge].id = jian; sys[sys_ge].ci = zhi; sys_ge++;
        }
    }
    qsort(sys, sys_ge, sizeof(struct jilu), bijiao_ci);

    int suan_ge = 0;
    __u32 jp = 0; __u64 hs = 0;
    while (bpf_map__get_next_key(qiti->maps.suanli_map, &jp, &jp, 4) == 0 && suan_ge < 256) {
        if (bpf_map__lookup_elem(qiti->maps.suanli_map, &jp, 4, &hs, 8, 0) == 0 && hs > 0) {
            if (!hai_zai((int)jp)) {
                bpf_map__delete_elem(qiti->maps.suanli_map, &jp, 4, 0);
                bpf_map__delete_elem(qiti->maps.kaishi_map, &jp, 4, 0);
                bpf_map__delete_elem(qiti->maps.ming_map, &jp, 4, 0);
                continue;
            }
            char ming[16] = {0};
            bpf_map__lookup_elem(qiti->maps.ming_map, &jp, 4, ming, 16, 0);
            __u64 ci_leiji = 0;
            for (int i = 0; i < shangci_suan_ge; i++) {
                if (shangci_suan[i].pid == jp) { ci_leiji = shangci_suan[i].zeng; break; }
            }
            zeng_l[suan_ge].pid = jp;
            zeng_l[suan_ge].zeng = hs >= ci_leiji ? hs - ci_leiji : hs;
            strncpy(zeng_l[suan_ge].ming, ming, 15); zeng_l[suan_ge].ming[15] = 0;
            suan[suan_ge].pid = jp; suan[suan_ge].haoshi = hs;
            strncpy(suan[suan_ge].ming, ming, 15); suan[suan_ge].ming[15] = 0;
            suan_ge++;
        }
    }
    qsort(zeng_l, suan_ge, sizeof(struct paiming_zeng), bijiao_zeng);
    shangci_suan_ge = suan_ge < 256 ? suan_ge : 256;
    for (int i = 0; i < shangci_suan_ge; i++) {
        shangci_suan[i].pid = suan[i].pid;
        shangci_suan[i].zeng = suan[i].haoshi;
    }

    int qih_ge = 0;
    char jc[16] = {0};
    while (bpf_map__get_next_key(qiti->maps.zhuanhuan_map, &jc, &jc, 16) == 0 && qih_ge < 256) {
        if (bpf_map__lookup_elem(qiti->maps.zhuanhuan_map, jc, 16, &zhi, 8, 0) == 0 && zhi > 0) {
            strncpy(qih[qih_ge].ming, jc, 15); qih[qih_ge].ming[15] = 0;
            qih[qih_ge].ci = zhi; qih_ge++;
        }
    }
    qsort(qih, qih_ge, sizeof(struct mingl), bijiao_qiehuan);

    __u64 zong_sys = 0;
    for (int i = 0; i < sys_ge; i++) zong_sys += sys[i].ci;
    __u64 qiehuan_zeng = qiehuan >= shangci_qiehuan ? qiehuan - shangci_qiehuan : qiehuan;
    __u64 sys_zeng = zong_sys >= shangci_total ? zong_sys - shangci_total : zong_sys;

    char duc[8192];
    int wei = 0;
    wei = jie_wen(duc, sizeof(duc), wei,
        "{\"shijian\":\"%02d:%02d:%02d\",\"lunci\":%d,\"jiedian\":\"%s\",\"cpu\":%.1f,\"neicun\":%ld,"
        "\"qiehuan\":%llu,\"qiehuan_zeng\":%llu,\"zhixing\":%llu,\"fanzhi\":%llu,"
        "\"zong_sys\":%llu,\"sys_zeng\":%llu,",
        xian->tm_hour, xian->tm_min, xian->tm_sec, lunci, jiedian, cpu, mem,
        (unsigned long long)qiehuan, (unsigned long long)qiehuan_zeng,
        (unsigned long long)zhixing,
        (unsigned long long)fanzhi, (unsigned long long)zong_sys,
        (unsigned long long)sys_zeng);
    wei = jie_wen(duc, sizeof(duc), wei, "\"sys_top\":[");
    for (int i = 0; i < sys_ge && i < 5; i++) {
        const char *ming = sys[i].id < 512 && mingling_ming[sys[i].id] ? mingling_ming[sys[i].id] : "?";
        wei = jie_wen(duc, sizeof(duc), wei, "%s{\"id\":%u,\"ming\":\"%s\",\"ci\":%llu}",
                      i ? "," : "", sys[i].id, ming, (unsigned long long)sys[i].ci);
    }
    wei = jie_wen(duc, sizeof(duc), wei, "],\"suanli_top\":[");
    char an_quan[24];
    for (int i = 0; i < suan_ge && i < 3; i++) {
        qing_ming(zeng_l[i].ming, an_quan, sizeof(an_quan));
        wei = jie_wen(duc, sizeof(duc), wei, "%s{\"pid\":%u,\"ming\":\"%s\",\"haoshi_ms\":%.0f}",
                      i ? "," : "", zeng_l[i].pid, an_quan, (double)zeng_l[i].zeng / 1e6);
    }
    wei = jie_wen(duc, sizeof(duc), wei, "],\"qiehuan_top\":[");
    for (int i = 0; i < qih_ge && i < 3; i++) {
        qing_ming(qih[i].ming, an_quan, sizeof(an_quan));
        wei = jie_wen(duc, sizeof(duc), wei, "%s{\"ming\":\"%s\",\"ci\":%llu}",
                      i ? "," : "", an_quan, (unsigned long long)qih[i].ci);
    }
    wei = jie_wen(duc, sizeof(duc), wei, "]}\n");
    printf("%s", duc);

    if (ku) {
        sqlite3_reset(charu);
        sqlite3_clear_bindings(charu);
        sqlite3_bind_text(charu, 1, jiedian, -1, SQLITE_STATIC);
        sqlite3_bind_double(charu, 2, cpu);
        sqlite3_bind_int64(charu, 3, mem);
        sqlite3_bind_int64(charu, 4, (long long)qiehuan);
        sqlite3_bind_int64(charu, 5, (long long)zong_sys);
        sqlite3_bind_text(charu, 6, duc, -1, SQLITE_STATIC);
        int zhuang = sqlite3_step(charu);
        if (zhuang != SQLITE_DONE) {
            sqlite3_reset(charu);
            lu_ku_bai++;
        } else {
            lu_ku_bai = 0;
        }
    }

    if (lu_ku_bai > 0 && lu_ku_bai != shangci_bai) {
        shangci_bai = lu_ku_bai;
        char neirong[128];
        snprintf(neirong, sizeof(neirong), "落库失败 %d 次", lu_ku_bai);
        cun_shijian(jiedian, "XITONG", neirong);
    }

    int zt;
    if (shangci_total > 0) {
        double zeng = 100.0 * sys_zeng / shangci_total;
        zt = bao_zhuangtai(&bao_sys, zeng > sys_yuzhi, 2);
        if (zt == 1) {
            char neirong[160];
            snprintf(neirong, sizeof(neirong), "syscall 激增 %.0f%%(上一周期 %llu 次)", zeng,
                     (unsigned long long)shangci_total);
            cun_shijian(jiedian, "ALARM", neirong);
        } else if (zt == -1) {
            char neirong[160];
            snprintf(neirong, sizeof(neirong), "syscall 回落 %.0f%%", zeng);
            cun_shijian(jiedian, "RECOVER", neirong);
        }
    }
    shangci_total = zong_sys;
    shangci_qiehuan = qiehuan;

    zt = bao_zhuangtai(&bao_cpu, cpu > cpu_yuzhi, 2);
    if (zt == 1) {
        char neirong[128];
        snprintf(neirong, sizeof(neirong), "CPU 占用 %.1f%% 连续超标", cpu);
        cun_shijian(jiedian, "ALARM", neirong);
    } else if (zt == -1) {
        char neirong[128];
        snprintf(neirong, sizeof(neirong), "CPU 恢复 %.1f%%", cpu);
        cun_shijian(jiedian, "RECOVER", neirong);
    }

    zt = bao_zhuangtai(&bao_mem, mem > mem_yuzhi, 2);
    if (zt == 1) {
        char neirong[128];
        snprintf(neirong, sizeof(neirong), "内存占用 %ld%% 连续超标", mem);
        cun_shijian(jiedian, "ALARM", neirong);
    } else if (zt == -1) {
        char neirong[128];
        snprintf(neirong, sizeof(neirong), "内存恢复 %ld%%", mem);
        cun_shijian(jiedian, "RECOVER", neirong);
    }

    if (suan_ge > 0 && zeng_l[0].zeng > 0) {
        double zhan = 100.0 * zeng_l[0].zeng / ((double)zhoudao * 1e9);
        zt = bao_zhuangtai(&bao_suanli, zhan > suanli_yuzhi, 2);
        if (zt == 1) {
            char neirong[128];
            snprintf(neirong, sizeof(neirong), "进程 %s 周期算力占用 %.0f%%", zeng_l[0].ming, zhan);
            cun_shijian(jiedian, "ALARM", neirong);
        } else if (zt == -1) {
            char neirong[128];
            snprintf(neirong, sizeof(neirong), "算力占用恢复 %.0f%%", zhan);
            cun_shijian(jiedian, "RECOVER", neirong);
        }
    } else {
        bao_zhuangtai(&bao_suanli, 0, 2);
    }

    if (zong_sys == 0) {
        lin_kong++;
        if (lin_kong == 5) {
            cun_shijian(jiedian, "XITONG", "探针连续 5 周期无数据,可能探针失效");
        }
    } else {
        lin_kong = 0;
    }

    free(sys); free(suan); free(zeng_l); free(qih);
}

int main(int jianshu, char *canshu[])
{
    setbuf(stdout, NULL);
    char jiedian_guo[64] = "weixing1";
    char ku_lu_guo[256] = "/var/log/weixing/weixing.db";
    if (du_zhi("jiedian", jiedian_guo, sizeof(jiedian_guo)) != 0) strcpy(jiedian_guo, "weixing1");
    if (du_zhi("ku_lu", ku_lu_guo, sizeof(ku_lu_guo)) != 0) strcpy(ku_lu_guo, "/var/log/weixing/weixing.db");
    const char *jiedian = jiedian_guo;
    int zhoudao = du_zhi_int("zhoudao", 5);
    int lunci = 0;
    const char *ku_lu = ku_lu_guo;
    sys_yuzhi = du_zhi_shuang("sys_yuzhi", 150.0);
    cpu_yuzhi = du_zhi_shuang("cpu_yuzhi", 85.0);
    mem_yuzhi = du_zhi_shuang("mem_yuzhi", 85.0);
    suanli_yuzhi = du_zhi_shuang("suanli_yuzhi", 50.0);
    if (jianshu > 1) jiedian = canshu[1];
    if (jianshu > 2) zhoudao = atoi(canshu[2]);
    if (jianshu > 3) ku_lu = canshu[3];

    char ku_lu_zui[512];
    char shijian_lu[512];
    struct stat st;
    if (stat(ku_lu, &st) == 0 && S_ISDIR(st.st_mode)) {
        snprintf(ku_lu_zui, sizeof(ku_lu_zui), "%s/%s.db", ku_lu, jiedian);
        snprintf(shijian_lu, sizeof(shijian_lu), "%s/%s.shijian", ku_lu, jiedian);
    } else {
        snprintf(ku_lu_zui, sizeof(ku_lu_zui), "%s", ku_lu);
        char xie[512];
        snprintf(xie, sizeof(xie), "%s", ku_lu);
        char *wei_xie = strrchr(xie, '/');
        if (wei_xie) *wei_xie = 0;
        else strcpy(xie, ".");
        snprintf(shijian_lu, sizeof(shijian_lu), "%s/%s.shijian", xie, jiedian);
    }

    ku = NULL;
    charu = NULL;
    shijian_charu = NULL;
    shijian_wen = fopen(shijian_lu, "a");
    if (sqlite3_open(ku_lu_zui, &ku) == SQLITE_OK) {
        sqlite3_exec(ku, "CREATE TABLE IF NOT EXISTS guance("
                         "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                         "jiedian TEXT, cpu REAL, neicun INTEGER,"
                         "qiehuan INTEGER, zong_sys INTEGER, duc TEXT,"
                         "shijian DEFAULT (datetime('now','localtime')))", 0, 0, 0);
        sqlite3_exec(ku, "CREATE TABLE IF NOT EXISTS shijian_biao("
                         "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                         "jiedian TEXT, leixing TEXT, neirong TEXT,"
                         "shijian DEFAULT (datetime('now','localtime')))", 0, 0, 0);
        sqlite3_prepare_v2(ku, "INSERT INTO guance(jiedian,cpu,neicun,qiehuan,zong_sys,duc) "
                               "VALUES(?1,?2,?3,?4,?5,?6)", -1, &charu, 0);
        sqlite3_prepare_v2(ku, "INSERT INTO shijian_biao(jiedian,leixing,neirong) "
                               "VALUES(?1,?2,?3)", -1, &shijian_charu, 0);
    } else {
        fprintf(stderr, "sqlite 打开失败,仅输出屏幕\n");
        ku = NULL;
    }

    struct agent_bpf *qiti = agent_bpf__open_and_load();
    if (!qiti) { fprintf(stderr, "open_and_load失败\n"); return 1; }
    if (agent_bpf__attach(qiti)) { fprintf(stderr, "attach失败: %s\n", strerror(errno)); agent_bpf__destroy(qiti); return 1; }

    signal(SIGINT, tingzhi);
    signal(SIGTERM, tingzhi);
    signal(SIGHUP, chong_du_peizhi);
    {
        char neirong[128];
        snprintf(neirong, sizeof(neirong), "qidong wanbi zhoudao=%ds", zhoudao);
        cun_shijian(jiedian, "XITONG", neirong);
    }
    printf("观测代理启动 节点=%s 周期=%ds ban_ben=%s\n", jiedian, zhoudao, BAN_BEN);
    while (jixu) {
        lunci++;
        if (chong_du) {
            chong_du = 0;
            sys_yuzhi = du_zhi_shuang("sys_yuzhi", 150.0);
            cpu_yuzhi = du_zhi_shuang("cpu_yuzhi", 85.0);
            mem_yuzhi = du_zhi_shuang("mem_yuzhi", 85.0);
            suanli_yuzhi = du_zhi_shuang("suanli_yuzhi", 50.0);
            cun_shijian(jiedian, "XITONG", "chong du pei zhi");
        }
        baogao(qiti, jiedian, lunci, zhoudao);
        if (lunci % 5 == 0) bao_zijian(jiedian);
        if (lunci % 100 == 0) qing_ku();
        for (int i = 0; i < zhoudao && jixu; i++) sleep(1);
    }
    cun_shijian(jiedian, "XITONG", "tuichu");
    if (shijian_charu) sqlite3_finalize(shijian_charu);
    if (charu) sqlite3_finalize(charu);
    if (ku) sqlite3_close(ku);
    if (shijian_wen) fclose(shijian_wen);
    agent_bpf__destroy(qiti);
    printf("观测代理退出\n");
    return 0;
}