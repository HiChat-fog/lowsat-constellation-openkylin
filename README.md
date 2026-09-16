# 低轨星座智能计算保障系统

RISC-V + openKylin 上的星座演示系统：星上 eBPF 观测代理、场景应用与异常检测引擎、星间心跳与故障自愈、云端调度与面板，配套系统裁剪管线与评估链。三台 QEMU riscv64 虚拟机模拟三颗星，宿主机承担云端角色，整套系统可在单台 Linux 主机上从零重建。

架构细节见 [ARCHITECTURE.md](ARCHITECTURE.md)，实测数据与逐项复现命令见 [DATA.md](DATA.md)

## 设计

两颗约束决定了系统形态。星上资源紧张，按 1GB 内存、2 vCPU 设计，常驻组件必须轻：观测代理是单个静态链接二进制，BPF 程序只挂四个探针。链路不可靠、节点会掉，于是三条通道各管一段：控制面与星间面走网络、要求实时，数据面走共享文件按存储转发，下行中断时云端看到文件变旧就判失联并停止派发，星上自治环路不受影响。

由此得到两条原则：接管者由节点名字典序决定，避免多节点同时接管；跨节点数据格式先写 schema 再写实现，两端以契约为准。

## 系统组成

| 目录 | 运行位置 | 职责 |
|---|---|---|
| `agent/` | 星上 | eBPF 观测采集：四探针、周期遥测、阈值告警、事件流与 SQLite 落库 |
| `gongju/` | 星上 | 场景应用：设备状态监测与检测引擎、电源系统健康管理（SOH/RUL）、采集工具、调度对比模拟器 |
| `xingxin/` | 星上 | 星间组网、心跳、任务执行、故障感知与任务接管（含分布式竞价转派） |
| `mianban/` | 云端 | 调度器、终端面板、指标报告、Prometheus 暴露器 |
| `hetong/` | 无 | 数据契约：遥测与事件 JSON schema、SQLite 表结构 |
| `pinggu/` | 云端 | 评估：合成序列对比、电源领域层对比、SMAP/MSL 公开数据对比、深度基线、理论校验、证据包 |
| `caijian/` | 云端 | 系统裁剪管线 |
| `jiaoben/` | 云端 | 部署、演示与真机实验脚本 |
| `memberlist/` | 星上 | 复用依赖：hashicorp/memberlist（未修改） |
| `waibu/` | 云端 | vendor：TSB-AD 评测协议 |

## 数据流

```
                 云端（宿主机）：调度器 / 面板 / 指标报告
                     │ 控制面 TCP 8011-8013 → 星上 7947
                     │ 数据面 9p 共享目录（遥测 JSON / SQLite / 任务结果）
                     ▼
   星间面：网桥 + tap 网卡 192.168.50.0/24（memberlist 心跳与任务派发）
   ┌──────────────┬──────────────┬──────────────┐
   │ 星1          │ 星2          │ 星3          │
   │ 观测代理      │ 观测代理      │ 观测代理      │
   │ 星间协同      │ 星间协同      │ 星间协同      │
   │ 场景应用      │ 场景应用      │ 场景应用      │
   └──────────────┴──────────────┴──────────────┘
```

## 关键指标

各项的样本量、方法与证据文件见 [DATA.md](DATA.md)。

| 项目 | 结果 |
|---|---|
| 镜像根分区占用 | 3.6 GB → 2.4 GB（-33.3%），一键裁剪管线 |
| 空闲内存占用 | -22.3% |
| 单节点故障恢复 | 2.9 秒（长任务在途时 kill 节点，负载转派路径） |
| 调度平均等待（仿真） | -32.5%，SJF 对比 FCFS，排队论交叉校验 |
| 异常检测（合成序列） | 100% 检出、零误报、四类类型全对（滑窗基线 50% 检出、21 次误报） |
| 异常检测（公开数据） | 点调整 F1 0.433、召回 0.988（NASA SMAP/MSL 四通道） |
| 电源领域层 | 六类注入故障全检出、瞬态零误报（通用引擎 4/5 检出） |
| 观测系统自身开销 | 约 1.2%（同一负载在观测代理开/关下的耗时对比） |

## 快速开始

依赖：`riscv64-linux-gnu-gcc`、`clang`、`bpftool`、内核源码树交叉编译出的 `libbpf.a`、Go 1.26+、QEMU、openKylin 2.0 SP2 riscv64 镜像与增强内核、Python 3。

```bash
make                                # 交叉编译全部二进制到 chengwu/
make ceshi                          # 门禁：C 自检 + pytest + Go(race/vet/staticcheck) + shellcheck/cppcheck

bash jiaoben/zhu_bei.sh             # 宿主机环境重建（网桥/tap、共享目录、二进制、软链接、自检）
python3 jiaoben/sanxing.py          # 三星全链路演示：组网 → 观测 → 派发 → 注入故障 → 自愈

./chengwu/agent_yonghu weixing1 5   # 单机跑观测代理（节点名 + 周期秒），遥测 JSON 输出到 stdout
```

配置在 `/etc/weixing/weixing.conf`，运行期 `SIGHUP` 重读阈值。

## 复现评估

```bash
python3 pinggu/duibi.py             # 合成序列：四类异常 vs 滑窗基线
python3 pinggu/dianyuan_duibi.py    # 电源领域层 vs 通用引擎
python3 pinggu/smap_duibi.py        # SMAP/MSL 点调整 F1 + TSB-AD 的 VUS-PR
python3 pinggu/shendu_jixian.py     # 自跑 LSTM 预测基线（参照上限）
python3 pinggu/diaodu_yanzheng.py   # 排队论交叉校验（KS 检验、Little 定律）
python3 pinggu/zheng_ju_bao.py      # 汇总以上全部为证据包（JSON + Markdown）
```

真机实验需要先把三星平台拉起来：

```bash
python3 jiaoben/shiyan_pingtai.py --qidong                  # 常驻平台（含本机控制端口）
python3 jiaoben/ab_shiyan.py --lunshu 10 --renwushu 40      # 真机调度 A/B（SJF vs FCFS）
python3 jiaoben/guzhang_jiaya.py --moshi kill9 --lunshu 10  # 故障注入：kill -9 / 断链 / 丢包
python3 jiaoben/kaixiao_jizhun.py --lunshu 10               # 观测代理自身开销基准
```

致谢：感谢我的好同学gyq和xcy，哈哈！本来是写给大创赛的，被刷了那就这样吧。

## 许可证

原创代码以 [Apache-2.0](LICENSE) 发布。随仓库分发的第三方组件（memberlist、TSB-AD）按各自许可证分发，见 [THIRD_PARTY.md](THIRD_PARTY.md)。
