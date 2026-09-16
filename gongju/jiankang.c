#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>

struct cpu_shuju { long zong; long kongxian; };

static struct cpu_shuju du_cpu(void)
{
    struct cpu_shuju r = { 0, 0 };
    FILE *f = fopen("/proc/stat", "r");
    if (!f) return r;
    char hang[512];
    while (fgets(hang, sizeof(hang), f)) {
        if (strncmp(hang, "cpu ", 4) == 0) {
            long a[8];
            int ge = sscanf(hang + 4, "%ld %ld %ld %ld %ld %ld %ld %ld",
                            &a[0], &a[1], &a[2], &a[3], &a[4], &a[5], &a[6], &a[7]);
            for (int i = 0; i < ge; i++) r.zong += a[i];
            r.kongxian = a[3] + a[4];
            break;
        }
    }
    fclose(f);
    return r;
}

static long du_hao(const char *lu, const char *guan_jian)
{
    FILE *f = fopen(lu, "r");
    if (!f) return -1;
    char hang[512];
    long jieguo = -1;
    while (fgets(hang, sizeof(hang), f)) {
        if (strstr(hang, guan_jian)) {
            char *p = hang;
            while (*p != ':' && *p) p++;
            p++;
            jieguo = atol(p);
            break;
        }
    }
    fclose(f);
    return jieguo;
}

int main(int jianshu, char *canshu[])
{
    (void)jianshu; (void)canshu;

    struct cpu_shuju q1 = du_cpu();
    sleep(1);
    struct cpu_shuju q2 = du_cpu();
    double zhanbi = 0;
    if (q2.zong > q1.zong)
        zhanbi = 100.0 * (q2.zong - q1.zong - (q2.kongxian - q1.kongxian)) / (q2.zong - q1.zong);
    if (zhanbi < 0) zhanbi = 0;

    time_t ke = time(NULL);
    struct tm *xian = localtime(&ke);
    printf("==== 节点状态快照 %02d:%02d:%02d ====\n", xian->tm_hour, xian->tm_min, xian->tm_sec);

    FILE *f = fopen("/proc/uptime", "r");
    double qidong = 0;
    if (f) { if (fscanf(f, "%lf", &qidong) != 1) qidong = 0; fclose(f); }
    printf("运行时间: %.0f 秒\n", qidong);

    double fu1, fu5, fu15;
    f = fopen("/proc/loadavg", "r");
    if (f) { if (fscanf(f, "%lf %lf %lf", &fu1, &fu5, &fu15) != 3) { fu1=fu5=fu15=0; } fclose(f); }
    printf("系统负载: %.2f / %.2f / %.2f\n", fu1, fu5, fu15);

    long zongnei = du_hao("/proc/meminfo", "MemTotal");
    long keyong = du_hao("/proc/meminfo", "MemAvailable");
    if (zongnei > 0 && keyong >= 0)
        printf("内存使用: %ld MB / %ld MB (%.1f%%)\n",
               (zongnei - keyong) / 1024, zongnei / 1024,
               100.0 * (zongnei - keyong) / zongnei);

    long jincheng = 0;
    FILE *pp = popen("ls /proc | grep -E '^[0-9]+$' | wc -l", "r");
    if (pp) { if (fscanf(pp, "%ld", &jincheng) != 1) jincheng = 0; pclose(pp); }
    printf("进程数量: %ld\n", jincheng);

    FILE *w = fopen("/sys/class/thermal/thermal_zone0/temp", "r");
    if (w) {
        long du = 0;
        if (fscanf(w, "%ld", &du) != 1) du = 0;
        fclose(w);
        printf("节点温度: %.1f 摄氏度\n", du / 1000.0);
    } else {
        printf("节点温度: 无传感器(虚拟环境,真机经hwmon采集)\n");
    }

    printf("CPU占用: %.1f%%\n", zhanbi);
    printf("功耗估算: %.2f W (按占用率线性模型,参考3W板级TDP)\n", 3.0 * zhanbi / 100);
    return 0;
}