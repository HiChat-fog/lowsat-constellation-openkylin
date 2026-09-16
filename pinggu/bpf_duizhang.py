#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import time

AGENT = os.environ.get("WX_AGENT_NATIVE", "/tmp/agent_native")
MI_AO = os.environ.get("WX_SUDO", "")
SHI_CHANG = int(os.environ.get("WX_SHI_CHANG", "20"))
ZHOU_QI = 2


def yun_dai_zhong(ming_ling, mi_aos=None):
    return subprocess.Popen(ming_ling, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True)


def main():
    if not os.path.exists(AGENT):
        sys.exit("que shao %s, xian bian yi yuan sheng agent" % AGENT)
    shu_chu = "/tmp/duizhang_agent.json"
    zhu_tai = "/tmp/duizhang_bpf.txt"
    open(shu_chu, "w").close()

    agent = subprocess.Popen(
        ["sudo", "-S", "sh", "-c",
         "ulimit -l unlimited; exec %s duizhang %d /tmp/duizhang.db" % (AGENT, ZHOU_QI)],
        stdin=subprocess.PIPE, stdout=open(shu_chu, "a"),
        stderr=subprocess.DEVNULL, text=True)
    try:
        agent.stdin.write(MI_AO + "\n")
        agent.stdin.flush()
    except Exception:
        pass
    time.sleep(3)

    bpf_cheng_xu = (
        "tracepoint:raw_syscalls:sys_enter { @sys = count(); }"
        "tracepoint:sched:sched_switch { @qh = count(); }"
        "tracepoint:sched:sched_process_exec { @zx = count(); }"
        "tracepoint:sched:sched_process_fork { @fz = count(); }"
        "interval:s:%d { print(@sys); print(@qh); print(@zx); print(@fz);"
        " clear(@sys); clear(@qh); clear(@zx); clear(@fz); }" % ZHOU_QI)
    bpf = subprocess.Popen(["sudo", "-S", "bpftrace", "-e", bpf_cheng_xu],
                           stdin=subprocess.PIPE, stdout=open(zhu_tai, "w"),
                           stderr=subprocess.DEVNULL, text=True)
    try:
        bpf.stdin.write(MI_AO + "\n")
        bpf.stdin.flush()
    except Exception:
        pass
    time.sleep(4)

    jie_shu = time.time() + SHI_CHANG
    mu_lu = ["/usr/share/doc", "/usr/include", "/usr/lib/python3.12"]
    i = 0
    while time.time() < jie_shu:
        mu = mu_lu[i % len(mu_lu)]
        subprocess.run("find %s -name '*.h' 2>/dev/null | head -300 > /dev/null; "
                       "grep -r 'include' /usr/include/sys 2>/dev/null | head -200 > /dev/null; "
                       "ls -laR /usr/share/doc 2>/dev/null | head -400 > /dev/null" % mu,
                       shell=True)
        i += 1

    time.sleep(1)
    bpf.terminate()
    agent.terminate()
    time.sleep(2)
    subprocess.run(["sudo", "-S", "pkill", "-f", "agent_native"],
                   input=MI_AO + "\n", capture_output=True, text=True)

    sys_zeng = qh_zeng = zx = fz = 0
    for hang in open(shu_chu):
        hang = hang.strip()
        if not hang.startswith("{"):
            continue
        try:
            g = json.loads(hang)
        except Exception:
            continue
        sys_zeng += g.get("sys_zeng", 0)
        qh_zeng += g.get("qiehuan_zeng", 0)
        zx = max(zx, g.get("zhixing", 0))
        fz = max(fz, g.get("fanzhi", 0))

    bpf_txt = open(zhu_tai).read()
    lei_ji = {"sys": 0, "qh": 0, "zx": 0, "fz": 0}
    for ming, zhi in re.findall(r"@(sys|qh|zx|fz): (\d+)", bpf_txt):
        lei_ji[ming] += int(zhi)
    bpf_sys, bpf_qh = lei_ji["sys"], lei_ji["qh"]
    bpf_zx, bpf_fz = lei_ji["zx"], lei_ji["fz"]

    print("=" * 64)
    print("  eBPF 观测交叉对账  agent(自研) vs bpftrace(独立工具)  同源探针")
    print("=" * 64)
    print("%-12s %14s %14s %8s" % ("计数器", "agent", "bpftrace", "偏差"))
    for ming, a, b in (("syscall", sys_zeng, bpf_sys),
                       ("sched_switch", qh_zeng, bpf_qh),
                       ("exec", zx, bpf_zx),
                       ("fork", fz, bpf_fz)):
        ji = max(a, b, 1)
        print("%-12s %14d %14d %7.1f%%" % (ming, a, b, 100.0 * abs(a - b) / ji))
    print("=" * 64)
    if os.environ.get("WX_DUIZHANG_JSON"):
        with open(os.environ["WX_DUIZHANG_JSON"], "w") as f:
            json.dump({"agent": {"sys": sys_zeng, "qiehuan": qh_zeng,
                                 "exec": zx, "fork": fz},
                       "bpftrace": {"sys": bpf_sys, "qiehuan": bpf_qh,
                                    "exec": bpf_zx, "fork": bpf_fz}}, f, indent=2)


if __name__ == "__main__":
    main()
