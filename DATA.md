# 实测数据与复现命令

**样本量的含义**：标注"确定性"的项目是固定随机种子或纯解析计算，重跑逐位一致；
标注 n=1 的是单次运行（多为管线或演示类，耗时长）。

## 一、系统裁剪

| 指标 | 实测 | 样本量 | 方法 |
|---|---|---|---|
| 根分区占用 | 3.6 GB → 2.4 GB，**-33.3%** | n=1 完整管线 | 服务精简、包移除、模块移除、深度校验（journal 清理等）、内存测量五步串行；基线为原始镜像的干净 overlay，不受历史运行影响。口径含 apt 缓存清理与文档/手册删除，不只是组件裁剪。 |
| 空闲内存占用 | **-22.3%** | n=1 | QEMU 内实测空闲内存对比。 |

```bash
# 目标镜像通过环境变量指定；每次运行在原始镜像的独立 overlay 上进行
WX_QCOW2=<原始镜像路径> python3 caijian/yijian.py
python3 caijian/ce_caijian_mem.py     # 内存测量
```

证据：裁剪各步的 df 采样输出在 QEMU 日志中（`/tmp/qemu_env/cj4.log`、`caijian2.log`、`caijian3.log`），
随运行环境生成，未入库。

## 二、星间协同与调度

| 指标 | 实测 | 样本量 | 说明 |
|---|---|---|---|
| 单节点故障恢复 | **2.9 秒**（设计目标 ≤60 秒） | n=1 演示 | 三星真机；注入在途长任务后 kill 承载节点，走负载转派路径完成任务接管。 |
| 调度平均等待（仿真） | **-32.5%** | 仿真多轮 | SJF 对比 FCFS；同一模拟器的到达间隔与服务时长通过 KS 检验、Little 定律校验。 |

```bash
python3 jiaoben/sanxing.py                                   # 三星全链路演示（含 60 秒自愈断言）
python3 jiaoben/shiyan_pingtai.py --qidong                   # 实验平台：三星常驻 + 控制端口
python3 jiaoben/ab_shiyan.py --lunshu 10 --renwushu 40 --bei 8 --bingfa 2
python3 jiaoben/guzhang_jiaya.py --moshi kill9 --lunshu 10   # 或 --moshi fenqu / diuban
python3 pinggu/diaodu_yanzheng.py                            # 排队论交叉校验
```

证据：`pinggu/chengguo/diaodu_yanzheng.json`（KS 检验 p 值、Little 定律偏差、SJF/FCFS 降幅）。

**A/B 实验的设计要点**：突发注入 40 个混合执行量的任务，云端派发速率高于三星执行能力，形成待发队列；
SJF 按执行量升序出队，FCFS 按创建序出队；任务实际执行耗时与预估执行量成正比（合成任务），所以
排序依据是真实有效的。星上并发设为 2（等于每颗星 vCPU 数），避免 CPU 超订把单任务拖过重派阈值。
每轮开始前重置三星（杀旧心跳进程、重启观测代理），保证轮与轮之间互不污染。

## 三、异常检测

| 指标 | 实测 | 样本量 | 说明 |
|---|---|---|---|
| 合成序列（四类异常） | 自适应引擎 **100% 检出、零误报、零过早恢复、四类类型全对**；滑窗 z 分数基线 50% 检出、21 次误报、2 次过早恢复（漏检卡死） | 确定性 | 900 拍序列，注入突变、漂移、方差爆发、卡死各一段。 |
| 电源领域层（六类注入故障） | 领域层 **5/5 段检出、瞬态误报 0**；通用引擎 4/5（母线跌落漏检）、瞬态误报 20 | 确定性 | 电源仿真 2000 拍，带真值标注；同时产出 SOH、RUL 与单次单粒子翻转事件。 |
| NASA SMAP/MSL（公开数据） | 自适应引擎点调整 F1 **0.433**、召回 **0.988**、误报点 8003（点级精确率 0.277）；滑窗基线 F1 0.395、召回 0.506；全局 3σ 基线 F1 0.414；T-1 通道自适应引擎 0.769、两个基线均为 0 | 确定性 | T-1、P-1、C-1、E-1 四通道（25/55 维）；另按 TSB-AD 协议计算 VUS-PR。 |
| 自跑 LSTM 基线（参照上限） | 点调整 F1 **0.817**、召回 0.990 | 确定性（固定种子） | torch CPU，窗长 64、单层 64 隐藏单元；训练窗剔除标注异常段防泄漏。协议与 Telemanom 论文不同，量纲不可直接排名。 |
| NASA PCoE 电池 RUL | B0005 平均相对误差 **20%**、B0006 **29%**（门槛 30%） | 2 组电池 | 18650 恒流放电真实老化数据，与 `dianyuan.c` 相同的滑动窗线性外推方法。 |

```bash
python3 pinggu/duibi.py             # 合成序列对比（门禁：自适应引擎必须优于基线，否则非零退出）
python3 pinggu/dianyuan_duibi.py    # 电源领域层 vs 通用引擎
python3 pinggu/smap_duibi.py        # SMAP/MSL 点调整 F1 + TSB-AD VUS-PR
python3 pinggu/shendu_jixian.py     # LSTM 预测基线（需 PyTorch；协议说明见 shendu_jixian_shuoming.md）
python3 pinggu/dianchi_yanzheng.py  # 电池 RUL 验证（需自备 PCoE 数据）
```

证据：`pinggu/chengguo/` 下的 `weixing_duibi_baogao.json`、`weixing_dianyuan_baogao.json`、
`weixing_smap_baogao.json`、`weixing_dianchi_baogao.json`，以及 `pinggu/shendu_jixian_jieguo.json`。

## 四、观测层与理论校验

| 指标 | 实测 | 样本量 | 说明 |
|---|---|---|---|
| 观测系统自身开销 | **约 1.2%** | n=2（冒烟级，建议按下方命令重跑 n=10） | 同一固定合成负载在 agent 开/关两种状态下的执行耗时对比；agent 自身 RSS 由自身遥测上报。 |
| bpftrace 交叉对账 | syscall 与调度切换计数偏差 18.9% / 13.6%（归因于两次测量的窗口错位）；exec/fork 计数见产物 | n=1 | 原生编译 agent 与 bpftrace 同源探针同时观测同一负载，独立外部工具校准。 |
| 排队论校验 | 到达间隔 KS 检验 p=0.80 / 服务时长 p=0.28；Little 定律偏差 3.4% | 确定性 | 验证调度模拟器的流量模型自洽性。 |

```bash
python3 jiaoben/kaixiao_jizhun.py --lunshu 10 --canliang 2000000 --xing 1   # 观测开销基准
python3 pinggu/bpf_duizhang.py                                              # 需真机 + bpftrace
```

证据：`pinggu/chengguo/kaixiao_jieguo.json`、`duizhang_jieguo.json`、`diaodu_yanzheng.json`。

## 五、工程门禁

| 项目 | 结果 |
|---|---|
| 测试门禁 | `make ceshi`：C 自检 + pytest 52 用例 + Go 17 用例（race/vet/staticcheck）+ shellcheck/cppcheck |
| CI | `.github/workflows/ceshi.yml`，无交叉工具链的环境自动跳过对应步骤 |
| 证据包 | `python3 pinggu/zheng_ju_bao.py` 一条命令汇总回归测试、三条对比评估、理论校验、bpftrace 对账、电池验证与真机断言，产出带时间戳的 JSON 与 Markdown |

## 数据来源与边界

- SMAP/MSL、PCoE 电池为公开数据集，评估脚本从本地数据目录读取。
- 合成序列、电源仿真、排队论模拟数据由脚本按固定种子生成，可逐位复现。
- 三星是 QEMU 虚拟机，星间链路是宿主机网桥，无真实射频链路与轨道动力学。
- 星上场景应用的数据源是带故障注入的仿真序列，`--shuru` 提供外部数据接入通道。
