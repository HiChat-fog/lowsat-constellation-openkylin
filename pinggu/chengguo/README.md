# 评估产物（证据文件）

本目录文件是评估脚本的原始输出，用于让每个指标都能追溯到具体产物。所有 JSON 都是脚本运行时
写出的，不是手工整理的。字段含义见各脚本与 [DATA.md](../../DATA.md)。

| 文件 | 由什么产生 | 内容 |
|---|---|---|
| `weixing_duibi_baogao.json` | `pinggu/duibi.py` | 合成 900 拍序列上优化方法与滑窗 z 分数基线的检出率、误报、过早恢复、类型正确性 |
| `weixing_dianyuan_baogao.json` | `pinggu/dianyuan_duibi.py` | 电源仿真 2000 拍上领域层与通用引擎的段检出、瞬态误报 |
| `weixing_smap_baogao.json` | `pinggu/smap_duibi.py` | NASA SMAP/MSL 四通道点调整 F1、召回、精确率、TP/FN，以及 TSB-AD 协议的 VUS-PR |
| `weixing_dianchi_baogao.json` | `pinggu/dianchi_yanzheng.py` | NASA PCoE 电池 B0005/B0006 的 RUL 预测平均相对误差 |
| `diaodu_yanzheng.json` | `pinggu/diaodu_yanzheng.py` | 排队论校验：到达间隔与服务时长 KS 检验 p 值、Little 定律偏差、SJF/FCFS 降幅 |
| `duizhang_jieguo.json` | `pinggu/bpf_duizhang.py` | agent 与 bpftrace 同源探针的计数对账（syscall、调度切换、exec、fork） |
| `kaixiao_jieguo.json` / `.md` | `jiaoben/kaixiao_jizhun.py` | 观测 agent 开/关两种状态下同一负载的执行耗时与 agent 自身 RSS |
| `kekaoxing_zhengju_*.json` | `pinggu/zheng_ju_bao.py` | 可靠性证据包：上述各项 + 回归测试 + 真机断言的汇总快照 |
| `ab_diaodu_jieguo.json` / `.md` | `jiaoben/ab_shiyan.py` | 真机 SJF vs FCFS 调度 A/B（多轮均值±标准差） |
| `guzhang_*_jieguo.json` / `.md` | `jiaoben/guzhang_jiaya.py` | 故障注入实验：感知时间、接管时间、丢包档位扫描 |

说明两点：

- 文件里的本机路径已替换为占位符（`$HOME`、`$QEMU_ENV`、`$(PROJECT_ROOT)`）。
- `ab_diaodu_jieguo.*` 与 `guzhang_*` 由真机实验产生，需要在三星平台驻留时运行对应脚本生成。
