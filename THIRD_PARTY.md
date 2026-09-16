# 第三方组件与许可证

本仓库的代码（agent/、gongju/、xingxin/、mianban/、pinggu/、caijian/、jiaoben/、hetong/、ceshi/）
以 Apache-2.0 发布，见 [LICENSE](LICENSE)。

以下组件不是本仓库原创，按各自许可证随仓库分发。使用时请遵守对应许可证。

## 随仓库分发的第三方代码

| 路径 | 组件 | 上游 | 许可证 | 说明 |
|---|---|---|---|---|
| `memberlist/` | hashicorp/memberlist | https://github.com/hashicorp/memberlist | MPL-2.0 | gossip 库，整体复用未修改。许可证全文见 `memberlist/LICENSE`。星间心跳/故障感知基于它构建（见 `xingxin/`）。MPL-2.0 为文件级 copyleft，未修改地放在独立目录内分发，不影响本仓库其余代码的许可证。 |
| `waibu/tsb_ad/` | TSB-AD 评测协议（TheDatumOrg） | https://github.com/TheDatumOrg/TSB-AD | Apache-2.0 | 异常检测评测协议（VUS-PR 等指标），vendor 进仓库以保证评测可复现。许可证全文见 `waibu/tsb_ad/LICENSE`。 |

## 随仓库分发的生成物（非第三方代码）

| 路径 | 内容 | 来源 |
|---|---|---|
| `gongju/vmlinux.h` | 内核 BTF 类型导出（约 11.9 万行生成物） | 由目标内核的 BTF 信息 dump 得到，CO-RE 编译需要。换成其它内核版本时需重新生成。 |
| `agent/mingling_tab.h` | riscv64 系统调用名表 | 由内核 UAPI 头文件提取生成。 |

## 构建与运行期依赖（不随仓库分发，需自行安装）

| 依赖 | 用途 | 许可证 |
|---|---|---|
| libbpf（内核源码树 `tools/lib/bpf`） | 用户态 BPF 加载 | LGPL-2.1 / BSD-2-Clause 双许可 |
| bpftool | 由 `.bpf.o` 生成骨架头文件 | GPL-2.0 / BSD-2-Clause |
| clang / LLVM | 编译 BPF 目标 | Apache-2.0 with LLVM exceptions |
| riscv64-linux-gnu-gcc | 交叉编译星上二进制 | GPL-3.0 |
| Go 工具链 | 交叉编译星间程序 | BSD-3-Clause |
| SQLite | 星上遥测落库 | Public Domain |
| QEMU | 三星仿真环境 | GPL-2.0 |
| openKylin 2.0 SP2（riscv64 镜像与增强内核） | 星上操作系统 | 各组件各自许可证 |
| Python 3 + numpy/scipy（评估脚本） | 检测评估与理论校验 | PSF / BSD-3-Clause |
| PyTorch（`pinggu/shendu_jixian.py`，可选） | 深度基线对比 | BSD-3-Clause |

## 数据来源

| 数据 | 来源 | 是否随仓库分发 |
|---|---|---|
| SMAP/MSL 公开数据集（T-1、P-1、C-1、E-1） | NASA JPL / telemanom 项目的公开标注数据 | 否，评估脚本从本地数据目录读取 |
| NASA PCoE 电池老化数据（B0005、B0006） | NASA Prognostics Center of Excellence 公开数据 | 否 |
| 合成序列、电源仿真、排队论模拟数据 | 本项目生成 | 由脚本按固定种子生成，可复现 |

## 复用声明

本仓库对 memberlist 的使用方式是"整体复用、不修改"（`xingxin/go.mod` 通过 `replace` 指向本地目录）。
若需升级 memberlist，替换 `memberlist/` 目录并保持其 `LICENSE` 文件完整即可。
