#!/usr/bin/env python3
"""LSTM 预测式异常检测基线 (学习型/神经网络基线)。

协议与 pinggu/smap_duibi.py 完全对齐:
  - 数据加载      : 复用 smap_duibi.jia_zai (np.load 单通道 .npy)
  - 标签构造      : 复用 smap_duibi.du_biao_qian (labeled_anomalies.csv,
                    anomaly_sequences 的 [start, end] 闭区间 -> 点级标签)
  - 点调整 F1     : 复用 smap_duibi.dian_tiao_zheng (point-adjust)

方法 (Telemanom, Hundman et al. KDD 2018 的轻量复现):
  按通道独立训练一个 LSTM, 用长 64 的滑动窗预测下一时刻向量;
  以预测误差的滑动均值平滑后, 用 mu + 3*sigma (k 全通道统一) 作为
  固定阈值打点级报警, 再套与 smap_duibi 相同的点调整 F1。
  阈值统计默认取训练段(剔除异常)误差; 仅 T-1 使用任务允许的一次
  校准: 用该通道最后 20% 无异常数据重估 mu/sigma (k 不变)。

与 Telemanom 原协议的差异 (诚实声明, 详见 shendu_jixian_shuoming.md):
  - 只有 test 通道数据, 无独立 train 集: 用序列前 min(1000, n/3) 个点
    作训练窗 (并剔除标注异常段防泄漏), 其余点与既有基线同口径参与评估;
  - 阈值用训练段误差的 mu + k*sigma (k=3.0 全通道统一), 不做逐通道调优;
  - CPU 单层小 LSTM, 非论文的 GPU 大模型 + 非参数动态阈值。

用法: python3 pinggu/shendu_jixian.py
输出: pinggu/shendu_jixian_jieguo.json
"""
import csv
import json
import os
import sys
import time

import numpy as np

BEN = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BEN)
# 复用现有评估协议的数据加载/标签/点调整F1 (来源: pinggu/smap_duibi.py)
from smap_duibi import (TONG_DAO, dian_tiao_zheng, du_biao_qian, jia_zai)

try:
    import torch
except ImportError:
    # 系统无 torch 时自动挂载同目录 venv (pip install torch --index-url
    # https://download.pytorch.org/whl/cpu 的安装位置)
    _venv = os.path.join(BEN, ".shendu_venv", "lib",
                         "python%d.%d" % sys.version_info[:2], "site-packages")
    if os.path.isdir(_venv):
        sys.path.append(_venv)
    import torch
import torch.nn as nn

# 小批量 LSTM 在多线程下有严重线程争用开销, 固定单线程 (已实测快一个量级)
torch.set_num_threads(1)

SHU_JU = os.environ.get(
    "WX_SMAP_SHUJU",
    os.path.join(BEN, "..", "..", "shiyan", "shuju_smap"))
JIE_GUO = os.environ.get(
    "WX_SHENDU_JIEGUO", os.path.join(BEN, "shendu_jixian_jieguo.json"))

CHUANG = 64          # 滑动窗长 (与任务要求的窗口口径一致)
PING_HUA = 10        # 预测误差滑动均值窗口
K_XISHU = 3.0        # 阈值系数 mu + k*sigma, 全通道统一, 不调参
EPOCH = 30
BATCH = 32
YIN_CANG = 64        # LSTM 隐藏单元
XUN_LIAN_SHANG_XIAN = 1000   # 训练窗上限: min(1000, n/3)
ZHONG_ZI = 0


class YuCeWang(nn.Module):
    """LSTM 下一时刻向量预测器。"""

    def __init__(self, wei_du, yin_cang=YIN_CANG):
        super().__init__()
        self.lstm = nn.LSTM(wei_du, yin_cang, num_layers=1, batch_first=True)
        self.shu_chu = nn.Linear(yin_cang, wei_du)

    def forward(self, x):
        h, _ = self.lstm(x)
        return self.shu_chu(h[:, -1, :])


def biao_ji_shu_zu(biao_qian, zong_chang):
    """与 smap_duibi.dian_biao_shu 同口径: [start, end] 闭区间置 1。"""
    biao = np.zeros(zong_chang, dtype=bool)
    for qi, zhi in biao_qian:
        biao[qi:min(zhi + 1, zong_chang)] = True
    return biao


def zhuang_chuang(xu, chuang):
    """滑动窗 -> (窗口数, chuang, 维度), 目标为每窗的下一时刻点。"""
    n, wei = xu.shape
    ge = np.lib.stride_tricks.sliding_window_view(xu, chuang, axis=0)
    ge = ge.transpose(0, 2, 1)              # (n-chuang+1, chuang, wei)
    mu_biao = xu[chuang:]                   # (n-chuang, wei) 下一时刻
    return ge[:-1], mu_biao                 # 末窗无目标, 去掉


def xun_lian_yi_huo(chuan, biao_qian):
    """返回 (训练张量对, 归一化参数, 训练窗终点, 剔除窗数)。

    防泄漏: 训练窗 = 前 min(1000, n/3) 个点; 归一化统计只统计其中
    非异常点; 任何与标注异常段相交的训练窗整窗剔除。
    """
    n, wei = chuan.shape
    xun_zhong = min(XUN_LIAN_SHANG_XIAN, n // 3)
    biao = biao_ji_shu_zu(biao_qian, n)
    gan_jing = ~biao[:xun_zhong]
    jun = chuan[:xun_zhong][gan_jing].mean(axis=0)
    fang = chuan[:xun_zhong][gan_jing].std(axis=0)
    fang[fang < 1e-9] = 1e-9
    gui = (chuan - jun) / fang

    chuang, mu_biao = zhuang_chuang(gui[:xun_zhong], CHUANG)
    # 窗 t 覆盖原序列 [t, t+chuang-1], 目标为 t+chuang; 任一与异常相交则剔除
    bao_liu = []
    for t in range(len(chuang)):
        qi, zhi = t, min(t + CHUANG, xun_zhong - 1)
        if not biao[qi:zhi + 1].any():
            bao_liu.append(t)
    zong_chuang = len(chuang)
    chuang = chuang[bao_liu]
    mu_biao = mu_biao[bao_liu]
    return chuang, mu_biao, jun, fang, gui, xun_zhong, zong_chuang - len(bao_liu)


def xun_lian_yi_lun(chuan, biao_qian):
    """训练一个通道的 LSTM, 返回 (模型, 归一化参数, 训练信息)。"""
    chuang, mu_biao, jun, fang, gui, xun_zhong, ti_chu = xun_lian_yi_huo(
        chuan, biao_qian)
    torch.manual_seed(ZHONG_ZI)
    np.random.seed(ZHONG_ZI)
    g = torch.Generator().manual_seed(ZHONG_ZI)
    mo = YuCeWang(chuan.shape[1])
    you = torch.optim.Adam(mo.parameters(), lr=1e-3)
    sun = nn.MSELoss()
    x = torch.tensor(chuang, dtype=torch.float32)
    y = torch.tensor(mu_biao, dtype=torch.float32)
    mo.train()
    for lun in range(EPOCH):
        pai = torch.randperm(len(x), generator=g)
        for qi in range(0, len(x), BATCH):
            su = pai[qi:qi + BATCH]
            you.zero_grad()
            c = sun(mo(x[su]), y[su])
            c.backward()
            you.step()
    return mo, jun, fang, gui, {"xun_lian_dian": int(xun_zhong),
                                "ti_chu_chuang": int(ti_chu),
                                "xun_lian_chuang": int(len(x))}


def yu_ce_wu_cha(mo, gui, jun, fang):
    """全序列预测误差 (逐点, 各维绝对误差均值), 前CHUANG点无预测记 nan。"""
    n = gui.shape[0]
    wu_cha = np.full(n, np.nan)
    chuang, _ = zhuang_chuang(gui, CHUANG)
    with torch.no_grad():
        yu = []
        for qi in range(0, len(chuang), 512):
            x = torch.tensor(chuang[qi:qi + 512], dtype=torch.float32)
            yu.append(mo(x).numpy())
        yu = np.concatenate(yu)
    zhen = gui[CHUANG:]
    wu_cha[CHUANG:] = np.abs(yu - zhen).mean(axis=1)
    return wu_cha


def bao_jing_shu_zu(wu_cha, biao_qian, xun_zhong, xiao_zhun=None):
    """误差滑动均值平滑; 阈值取校准段平滑误差的 mu+k*sigma。

    校准段默认为训练段(剔除异常点); 若给定 xiao_zhun 索引数组则改用它
    (仅 T-1 允许的一次校准, 用最后20%无异常数据)。
    返回 (点级报警布尔数组, (mu, sigma, yu_zhi))。
    """
    n = len(wu_cha)
    ping = np.full(n, np.nan)
    for t in range(CHUANG, n):
        ping[t] = np.nanmean(wu_cha[max(0, t - PING_HUA + 1):t + 1])
    biao = biao_ji_shu_zu(biao_qian, n)
    if xiao_zhun is None:
        xiao_zhun = np.arange(CHUANG, xun_zhong)
    xiao_zhun = xiao_zhun[~biao[xiao_zhun] & ~np.isnan(ping[xiao_zhun])]
    mu, sigma = float(ping[xiao_zhun].mean()), float(ping[xiao_zhun].std())
    yu_zhi = mu + K_XISHU * sigma
    huo = np.zeros(n, dtype=bool)
    huo[CHUANG:] = ping[CHUANG:] > yu_zhi
    return huo, (mu, sigma, yu_zhi)


def main():
    np.random.seed(ZHONG_ZI)
    hui_zong = {
        "fang_fa": "LSTM预测基线(学习型): 滑窗64预测下一时刻, 误差滑动均值+mu/3sigma阈值",
        "kuang_jia": "torch %s (CPU)" % torch.__version__,
        "sui_ji_zhong_zi": ZHONG_ZI,
        "chao_can": {"chuang": CHUANG, "ping_hua": PING_HUA, "k": K_XISHU,
                     "epoch": EPOCH, "batch": BATCH, "yin_cang": YIN_CANG,
                     "xun_lian_shang_xian": XUN_LIAN_SHANG_XIAN,
                     "lr": 1e-3, "sun_shi": "MSE", "you_hua": "Adam",
                     "torch_threads": 1},
        "fang_xie_lou": ("训练窗=序列前min(1000,n/3)点; 归一化统计只含训练窗内"
                         "非异常点; 与标注异常段相交的训练窗整窗剔除"),
        "xiao_zhun_shuo_ming": (
            "阈值系数k=3.0全通道统一不调参; 仅通道T-1使用一次阈值校准"
            "(任务允许): 校准段=最后20%无异常数据(再剔除残余异常点), "
            "用其平滑预测误差重估mu/sigma(k不变); 其余通道用训练段误差估计; "
            "校准仅用无异常数据估阈值, 未对标签调优"),
        "xie_yi_shuo_ming": ("评估协议(数据加载/标签/点调整F1)复用 pinggu/smap_duibi.py;"
                             " 全序列打点级报警, 前CHUANG点无法预测不报警"),
        "tong_dao": {}, "zong": {}}
    zong_tp = zong_fp = zong_fn = 0
    for chan_id in TONG_DAO:
        kai_shi = time.time()
        chuan = jia_zai(chan_id).astype(np.float32)
        biao_qian = du_biao_qian(chan_id)
        mo, jun, fang, gui, xin_xi = xun_lian_yi_lun(chuan, biao_qian)
        wu_cha = yu_ce_wu_cha(mo, gui, jun, fang)
        # 仅 T-1: 任务允许的一次阈值校准, 用最后20%无异常数据重估 mu/sigma
        xiao_zhun = None
        xiao_xin = None
        if chan_id == "T-1":
            zong_chang = len(chuan)
            qi0 = int(zong_chang * 0.8)
            quan_biao = biao_ji_shu_zu(biao_qian, zong_chang)
            suo = np.arange(qi0, zong_chang)
            suo = suo[~quan_biao[suo]]
            xiao_zhun = suo
            xiao_xin = {"qu_jian": [int(qi0), int(zong_chang - 1)],
                        "wu_yi_chang_dian_shu": int(len(suo))}
        # 校准前结果(用训练段阈值)仅作透明记录
        huo_qian, (mu_q, sg_q, yz_q) = bao_jing_shu_zu(
            wu_cha, biao_qian, xin_xi["xun_lian_dian"])
        zhi_qian = dian_tiao_zheng([bool(v) for v in huo_qian], biao_qian)
        huo, (mu, sigma, yu_zhi) = bao_jing_shu_zu(wu_cha, biao_qian,
                                                   xin_xi["xun_lian_dian"],
                                                   xiao_zhun)
        zhi = dian_tiao_zheng([bool(v) for v in huo], biao_qian)
        zhi["xun_lian_miao"] = round(time.time() - kai_shi, 1)
        zhi["xun_lian_chuang_kou"] = xin_xi["xun_lian_chuang"]
        zhi["ti_chu_chuang"] = xin_xi["ti_chu_chuang"]
        zhi["xun_lian_dian"] = xin_xi["xun_lian_dian"]
        zhi["yu_zhi"] = {"mu": round(mu, 6), "sigma": round(sigma, 6),
                         "yu_zhi": round(yu_zhi, 6), "k": K_XISHU,
                         "xiao_zhun": xiao_xin}
        zhi["xiao_zhun_qian"] = {
            "shuo_ming": "用训练段阈值(未校准)的结果, 仅作透明记录",
            "f1": zhi_qian["f1"], "zhao_hui": zhi_qian["zhao_hui"],
            "jing_que": zhi_qian["jing_que"], "duan_zhao": zhi_qian["duan_zhao"],
            "yu_zhi": round(yz_q, 6)}
        hui_zong["tong_dao"][chan_id] = zhi
        zong_tp += zhi["tp"]; zong_fp += zhi["fp"]; zong_fn += zhi["fn"]
        print("%s: F1=%.3f 召回=%.3f 精确=%.3f 段检出=%d/%d 用时=%.1fs "
              "训练窗=%d 剔除窗=%d" %
              (chan_id, zhi["f1"], zhi["zhao_hui"], zhi["jing_que"],
               zhi["duan_zhao"], len(biao_qian), zhi["xun_lian_miao"],
               zhi["xun_lian_chuang_kou"], zhi["ti_chu_chuang"]))
    jing = zong_tp / (zong_tp + zong_fp) if zong_tp + zong_fp else 0.0
    zhao = zong_tp / (zong_tp + zong_fn) if zong_tp + zong_fn else 0.0
    f1 = 2 * jing * zhao / (jing + zhao) if jing + zhao else 0.0
    hui_zong["zong"] = {"f1": round(f1, 3), "zhao_hui": round(zhao, 3),
                        "jing_que": round(jing, 3)}
    with open(JIE_GUO, "w") as f:
        json.dump(hui_zong, f, ensure_ascii=False, indent=2)
    print("总F1=%.3f 召回=%.3f 精确=%.3f  已写入 %s" %
          (f1, zhao, jing, JIE_GUO))


if __name__ == "__main__":
    main()
