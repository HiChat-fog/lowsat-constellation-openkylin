/* guanlan_agent.c — telemetry agent for the nommu openKylin constellation node.
 *
 * Emits one JSON line per sampling period in the lowsat "guance-shuju" data
 * contract (version 1.1), from /proc sources only: no eBPF on nommu, so the
 * syscall-level fields (zong_sys, sys_zeng, sys_top, qiehuan_top, zhixing)
 * are honestly zeroed/emptied. Context switches, forks, CPU and memory come
 * from /proc/stat and /proc/meminfo; per-process CPU time (suanli_top) from
 * /proc/<pid>/stat deltas.
 *
 * Usage: guanlan_agent <node> <period_sec> <out_path>
 *   e.g. guanlan_agent weixing4 3 /mnt/share/shuju/weixing4.json
 * The output file is truncated at start (same semantics as the fleet's
 * "agent > file" redirect), appended per period, flushed every line so the
 * host side sees live data through 9p.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <time.h>
#include <unistd.h>

#define MAXP 64          /* tracked processes */
#define SUANLI_TOP 3     /* contract: top 3 */

struct pcpu {           /* cumulative per-process cpu ticks */
	int pid;
	unsigned long ticks;
	char name[24];
};

struct snap {           /* /proc/stat snapshot */
	unsigned long long ctxt, forks;
	unsigned long long cpu[8];   /* user nice system idle iowait irq softirq steal */
	int ncpu;
};

static long hz = 100;

static int is_num(const char *s)
{
	for (; *s; s++)
		if (!isdigit((unsigned char)*s))
			return 0;
	return 1;
}

static void sanitize(char *d, const char *s, size_t n)
{
	size_t i;
	for (i = 0; i + 1 < n && s[i]; i++)
		d[i] = isalnum((unsigned char)s[i]) || s[i] == '_' ? s[i] : '_';
	d[i] = 0;
}

static int read_proc_stat(struct snap *s)
{
	FILE *f = fopen("/proc/stat", "r");
	char line[512];
	int i;

	if (!f)
		return -1;
	while (fgets(line, sizeof(line), f)) {
		if (!strncmp(line, "cpu ", 4)) {
			i = sscanf(line + 4, "%llu %llu %llu %llu %llu %llu %llu %llu",
				&s->cpu[0], &s->cpu[1], &s->cpu[2], &s->cpu[3],
				&s->cpu[4], &s->cpu[5], &s->cpu[6], &s->cpu[7]);
			s->ncpu = i;
		} else if (!strncmp(line, "ctxt ", 5)) {
			s->ctxt = strtoull(line + 5, NULL, 10);
		} else if (!strncmp(line, "processes ", 10)) {
			s->forks = strtoull(line + 10, NULL, 10);
		}
	}
	fclose(f);
	return 0;
}

static int read_mem_pct(void)
{
	FILE *f = fopen("/proc/meminfo", "r");
	char line[256];
	long total = -1, avail = -1;

	if (!f)
		return -1;
	while (fgets(line, sizeof(line), f)) {
		if (!strncmp(line, "MemTotal:", 9))
			total = strtol(line + 9, NULL, 10);
		else if (!strncmp(line, "MemAvailable:", 13))
			avail = strtol(line + 13, NULL, 10);
	}
	fclose(f);
	if (total <= 0 || avail < 0)
		return -1;
	return (int)((total - avail) * 100 / total);
}

/* per-process cumulative cpu ticks; returns count tracked */
static int read_procs(struct pcpu *out, int max)
{
	DIR *d = opendir("/proc");
	struct dirent *e;
	int n = 0;

	if (!d)
		return 0;
	while ((e = readdir(d)) && n < max) {
		char path[64], buf[512], name[24];
		char *lp, *rp, *tok;
		unsigned long ut = 0, st = 0;
		int field, pid;
		FILE *f;
		size_t len;

		if (!is_num(e->d_name))
			continue;
		snprintf(path, sizeof(path), "/proc/%s/stat", e->d_name);
		f = fopen(path, "r");
		if (!f)
			continue;           /* process died mid-scan */
		if (!fgets(buf, sizeof(buf), f)) {
			fclose(f);
			continue;
		}
		fclose(f);
		lp = strchr(buf, '(');
		rp = strrchr(buf, ')');
		if (!lp || !rp || rp <= lp)
			continue;
		len = (size_t)(rp - lp - 1);
		if (len >= sizeof(name))
			len = sizeof(name) - 1;
		memcpy(name, lp + 1, len);
		name[len] = 0;
		pid = atoi(buf);

		/* fields after comm: state(3) ... utime(14) stime(15) */
		field = 2;
		tok = rp + 1;
		while (tok && *tok && field < 15) {
			char *nx = strchr(tok, ' ');
			if (nx)
				*nx = 0;
			field++;
			if (field == 14)
				ut = strtoul(tok, NULL, 10);
			else if (field == 15)
				st = strtoul(tok, NULL, 10);
			tok = nx ? nx + 1 : NULL;
		}
		out[n].pid = pid;
		out[n].ticks = ut + st;
		sanitize(out[n].name, name, sizeof(out[n].name));
		n++;
	}
	closedir(d);
	return n;
}

/* match cumulative ticks of pid in previous snapshot */
static unsigned long prev_ticks(struct pcpu *prev, int np, int pid)
{
	int i;
	for (i = 0; i < np; i++)
		if (prev[i].pid == pid)
			return prev[i].ticks;
	return 0;
}

static void emit(FILE *out, const char *node, long lunci, struct snap *cur,
	struct snap *prev, struct pcpu *pcur, int np,
	struct pcpu *pprev, int npp, int mem_pct)
{
	unsigned long long busy = 0, total = 0, ctxt_d = 0;
	unsigned long delta[MAXP], ms[MAXP];
	struct pcpu *top[SUANLI_TOP];
	int ntop = 0, i, j;
	time_t t = time(NULL);
	struct tm tm;

	localtime_r(&t, &tm);
	for (i = 0; i < 8; i++) {
		unsigned long long d = cur->cpu[i] >= prev->cpu[i] ?
			cur->cpu[i] - prev->cpu[i] : 0;
		total += d;
		if (i != 3)             /* field 3 is idle */
			busy += d;
	}
	ctxt_d = cur->ctxt >= prev->ctxt ? cur->ctxt - prev->ctxt : 0;

	fprintf(out,
		"{\"shijian\":\"%02d:%02d:%02d\",\"lunci\":%ld,\"jiedian\":\"%s\","
		"\"cpu\":%llu.%llu,\"neicun\":%d,"
		"\"qiehuan\":%llu,\"qiehuan_zeng\":%llu,"
		"\"zhixing\":0,\"fanzhi\":%llu,"
		"\"zong_sys\":0,\"sys_zeng\":0,"
		"\"sys_top\":[],\"suanli_top\":[",
		tm.tm_hour, tm.tm_min, tm.tm_sec, lunci, node,
		total ? busy * 100 / total : (unsigned long long)0,
		total ? (busy * 1000 / total) % 10 : (unsigned long long)0,
		mem_pct < 0 ? 0 : mem_pct,
		cur->ctxt, ctxt_d, cur->forks);

	for (i = 0; i < np; i++) {
		unsigned long pd = pcur[i].ticks >=
			prev_ticks(pprev, npp, pcur[i].pid) ?
			pcur[i].ticks - prev_ticks(pprev, npp, pcur[i].pid) : 0;

		delta[i] = pd;
		ms[i] = hz ? pd * 1000 / hz : 0;
	}
	for (i = 0; i < np; i++) {          /* selection of top SUANLI_TOP */
		int best = -1;

		for (j = 0; j < np; j++) {
			int taken = 0, k;

			for (k = 0; k < ntop; k++)
				if (top[k] == &pcur[j])
					taken = 1;
			if (taken)
				continue;
			if (best < 0 || delta[j] > delta[best])
				best = j;
		}
		if (best < 0 || delta[best] == 0)
			break;
		top[ntop++] = &pcur[best];
	}
	for (i = 0; i < ntop; i++)
		fprintf(out, "%s{\"pid\":%d,\"ming\":\"%s\",\"haoshi_ms\":%lu}",
			i ? "," : "", top[i]->pid, top[i]->name, ms[top[i] - pcur]);
	fprintf(out, "],\"qiehuan_top\":[]}\n");
	fflush(out);
}

/* flat binaries get a small stack by default; keep big buffers off it */
static struct snap prev, cur;
static struct pcpu pprev[MAXP], pcur[MAXP];

int main(int argc, char **argv)
{
	const char *node;
	int period;
	FILE *out;
	int npp = 0, np;
	long lunci = 0;
	long v;

	if (argc != 4) {
		fprintf(stderr, "usage: %s <node> <period_sec> <out_path>\n", argv[0]);
		return 1;
	}
	node = argv[1];
	period = atoi(argv[2]);
	if (period < 1)
		period = 3;
	v = sysconf(_SC_CLK_TCK);
	if (v > 0)
		hz = v;

	out = fopen(argv[3], "w");      /* truncate at start, like "agent > file" */
	if (!out) {
		fprintf(stderr, "cannot open %s: %s\n", argv[3], strerror(errno));
		return 1;
	}

	memset(&prev, 0, sizeof(prev));
	memset(&cur, 0, sizeof(cur));
	memset(pprev, 0, sizeof(pprev));

	for (;;) {
		int mem = read_mem_pct();

		read_proc_stat(&cur);
		np = read_procs(pcur, MAXP);

		emit(out, node, ++lunci, &cur, &prev, pcur, np, pprev, npp, mem);

		prev = cur;
		memcpy(pprev, pcur, sizeof(pcur));
		npp = np;
		sleep(period);
	}
	return 0;
}
