# weixing4：nommu openKylin 星座节点

星座的第四颗星：openKylin nile 内核（6.6）去掉 MMU（CONFIG_MMU=n，rv32，M 态）
跑起来的节点，与 weixing1-3 使用同一份数据契约和同一条 9p 数据通路。
云端与面板零代码改动——`peizhi/yunduan.conf` 里加一行 `weixing4=` 即可在面板上
多出该节点；"15 秒无上报判失联 + 任务转派"天然覆盖它。

## 组成

- `guanlan_agent.c`：遥测 agent，按 `hetong/guance.schema.json`（guance-shuju 契约
  v1.1）的 14 字段输出 JSON 行。数据源 /proc；nommu 内核无 eBPF，syscall 级字段
  （zong_sys/sys_zeng/sys_top/qiehuan_top/zhixing）诚实置零，suanli_top 取自
  /proc/<pid>/stat 的周期增量。
- `overlay/etc/init.d/S99guanlan`：开机挂 9p 并启动 agent（写入
  /mnt/share/shuju/weixing4.json，经 9p 实时落盘到宿主共享目录）。
- `kernel-config-9p.fragment`：内核配置增量与三个踩坑说明。
- `patches/0001-linkyum-guard.patch`：nile 树 vendor 驱动的 Kconfig 卫生修正。

## 复现路径（概要）

1. 内核：openKylin nile 源码（6.6.x），`make ARCH=riscv nommu_virt_defconfig
   32-bit.config`，叠加 `kernel-config-9p.fragment` 所列项，产物
   `arch/riscv/boot/Image`（约 2.3MB）。
2. 用户态：buildroot `qemu_riscv32_nommu_virt_defconfig`（riscv32 noMMU，
   uClibc-ng + busybox BFLT），rootfs.ext2。
3. agent 编译（buildroot 工具链，必须 `-fPIC`，gcc bug 79509，缺它必段错误）：
   `riscv32-buildroot-linux-uclibc-gcc -O2 -fPIC -o guanlan_agent guanlan_agent.c \
    -Wl,-elf2flt=-r -Wl,-elf2flt=-s16384`（产物为 BFLT v4）。
4. 启动（QEMU 8.2+）：
   ```
   qemu-system-riscv32 -M virt -bios none -kernel Image -nographic -cpu rv32,mmu=off \
     -append "rootwait root=/dev/vda ro console=ttyS0" \
     -drive file=rootfs.ext2,format=raw,id=hd0,if=none \
     -device virtio-blk-device,drive=hd0 \
     -fsdev local,id=fsdev0,path=<宿主共享目录>,security_model=none \
     -device virtio-9p-device,fsdev=fsdev0,mount_tag=hostshare
   ```
   注意：9p 用 MMIO 设备形态（内核未开 PCI 时 `-virtfs` 的 PCI 形态不可见）。

## 三个容易踩的坑（详见提交讨论）

- `CONFIG_CMDLINE_FORCE=y` 会把外部 cmdline 整个顶掉（init= 等参数消失）；
- 内置 initramfs 会抢根，`root=/dev/vda` 不再挂载，须清空 INITRAMFS_SOURCE；
- flat 二进制缺 `-fPIC` 时加载即段错误（固定低地址 store fault），与 BFLT 生成
  无关，报错不指向真因。

## 验收

- 面板侧用本仓库 `mianban/yunduan_mianban.py` 的 `du_xin("weixing4")` 解析通过；
- 契约 14 字段类型校验 14/14 PASS；
- 杀节点后 mtime 超 15 秒，失联判停正确触发。
