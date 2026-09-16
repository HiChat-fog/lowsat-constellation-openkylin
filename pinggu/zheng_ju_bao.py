#!/usr/bin/env python3
import glob
import json
import os
import re
import subprocess
import sys
import time

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHU_CHU = os.environ.get("WX_ZHENGJU", "/tmp/kekaoxing_zhengju")
LA_HENG = "/tmp/qemu_env/sanxing_benci.log"


def du_json(lu):
    try:
        with open(lu) as f:
            return json.load(f)
    except Exception:
        return None


def sanxing_zhai_yao():
    try:
        with open(LA_HENG) as f:
            txt = f.read()
        shu = re.search(r"断言 (\d+)/(\d+) 通过", txt)
        if not shu:
            return None
        tong = 0
        for m in re.finditer(r"接管完成 (\S+) 恢复用时 (\d+) 毫秒", txt):
            tong = max(tong, int(m.group(2)))
        hui = re.findall(r"恢复用时 (\d+) 毫秒", txt)
        return {"duan_yan": "%s/%s" % (shu.group(1), shu.group(2)),
                "zui_hao_hui_fu_ms": min(int(x) for x in hui) if hui else None,
                "hui_fu_hao_miao": [int(x) for x in hui]}
    except Exception:
        return None


def main():
    bao = {"shi_jian": time.strftime("%Y-%m-%d %H:%M:%S"), "mo_kuai": {}}

    he_dui = subprocess.run(["make", "ceshi"], cwd=GEN, capture_output=True, text=True, timeout=1200)
    py = re.findall(r"(\d+) passed(?:, (\d+) skipped)?", he_dui.stdout)
    bao["mo_kuai"]["hui_gui_ce_shi"] = {
        "pytest": ("通过 " + py[0][0] + (" 跳过 " + py[0][1] if py[0][1] else "")) if py else "wei_zhi",
        "tui_chu_ma": he_dui.returncode}

    dui = du_json("/tmp/weixing_duibi_baogao.json")
    if dui:
        bao["mo_kuai"]["he_cheng_dui_bi"] = {
            "you_hua": {"jian_chu_lv": dui["you_hua"]["jian_chu_lv"],
                        "wu_bao": dui["you_hua"]["wu_bao"]},
            "ji_xian": {"jian_chu_lv": dui["ji_xian"]["jian_chu_lv"],
                        "wu_bao": dui["ji_xian"]["wu_bao"]}}

    smap = du_json("/tmp/weixing_smap_baogao.json")
    if smap:
        z = {"can_zhao": smap.get("can_zhao", {})}
        for m, v in smap["fang_fa"].items():
            z[m] = {"f1": v["zong_f1"], "zhao_hui": v["zong_zhao_hui"],
                    "vus_pr": v.get("tsb_ad_vus_pr")}
        bao["mo_kuai"]["smap_msl"] = z

    dy = du_json("/tmp/weixing_dianyuan_baogao.json")
    if dy:
        bao["mo_kuai"]["dian_yuan_ling_yu"] = {
            "ling_yu": dy["ling_yu"], "tong_yong": dy["tong_yong"],
            "soh": dy.get("soh"), "rul": dy.get("rul")}

    yz = du_json("/tmp/diaodu_yanzheng.json")
    if yz:
        bao["mo_kuai"]["diao_du_li_lun_yan_zheng"] = yz

    dc = du_json("/tmp/weixing_dianchi_baogao.json")
    if dc:
        bao["mo_kuai"]["dian_chi_zhen_shi_shu_ju"] = dc

    bz = du_json("/tmp/duizhang_jieguo.json")
    if bz:
        bao["mo_kuai"]["bpf_jiao_cha_dui_zhang"] = bz

    sx = sanxing_zhai_yao()
    if sx:
        bao["mo_kuai"]["san_xing_zhen_ji_yan_shi"] = sx

    with open(SHU_CHU + ".json", "w") as f:
        json.dump(bao, f, ensure_ascii=False, indent=2)
    hang = ["# 可靠性证据包  %s" % bao["shi_jian"], ""]
    mk = bao["mo_kuai"]
    if "hui_gui_ce_shi" in mk:
        hang.append("- 回归测试: %s (退出码 %d)" %
                    (mk["hui_gui_ce_shi"]["pytest"], mk["hui_gui_ce_shi"]["tui_chu_ma"]))
    if "he_cheng_dui_bi" in mk:
        z = mk["he_cheng_dui_bi"]
        hang.append("- 合成注入对比: 优化 检出%s/误报%d vs 基线 检出%s/误报%d" %
                    (z["you_hua"]["jian_chu_lv"], z["you_hua"]["wu_bao"],
                     z["ji_xian"]["jian_chu_lv"], z["ji_xian"]["wu_bao"]))
    if "smap_msl" in mk:
        z = mk["smap_msl"]
        hang.append("- SMAP/MSL(公开数据): " + "; ".join(
            "%s F1=%.3f VUS-PR=%s" % (m, v["f1"], v.get("vus_pr")) for m, v in z.items()
            if isinstance(v, dict) and "f1" in v))
        if z.get("can_zhao"):
            hang.append("  参照系: %s 汇总 F1 SMAP=%.2f/MSL=%.2f (离线GPU)" %
                        (z["can_zhao"]["fang_fa"], z["can_zhao"]["hui_zong"]["SMAP"],
                         z["can_zhao"]["hui_zong"]["MSL"]))
    if "dian_yuan_ling_yu" in mk:
        z = mk["dian_yuan_ling_yu"]
        hang.append("- 电源领域层: 检出 %d/%d, 瞬态误报 %d (通用引擎 %d/%d, %d)" %
                    (z["ling_yu"]["duan_jian_chu"], z["ling_yu"]["duan_zong"],
                     z["ling_yu"]["guo_du_wu_bao"], z["tong_yong"]["duan_jian_chu"],
                     z["tong_yong"]["duan_zong"], z["tong_yong"]["guo_du_wu_bao"]))
    if "diao_du_li_lun_yan_zheng" in mk:
        z = mk["diao_du_li_lun_yan_zheng"]
        hang.append("- 调度理论校验: KS p=%s/%s, Little 偏差 %s%%, SJF 降幅 %s%%" %
                    (z["lv_bo_kc_p"], z["fu_wu_kc_p"], z["little_pian_cha"], z["sjf_jiang"]))
    if "dian_chi_zhen_shi_shu_ju" in mk:
        z = mk["dian_chi_zhen_shi_shu_ju"]
        hang.append("- NASA 电池真实老化数据: " + "; ".join(
            "%s 平均RUL误差 %s" % (c, v["jun_xiang_dui_wu_cha"]) for c, v in z["dian_chi"].items()))
    if "bpf_jiao_cha_dui_zhang" in mk:
        z = mk["bpf_jiao_cha_dui_zhang"]
        ming_lie = [("exec", "exec"), ("fork", "fork"), ("syscall", "sys"), ("切换", "qiehuan")]
        xiang = []
        for xian_shi, jian in ming_lie:
            a_zhi = z.get("agent", {}).get(jian)
            b_zhi = z.get("bpftrace", {}).get(jian)
            if a_zhi is not None and b_zhi is not None:
                xiang.append("%s 偏差 %.1f%%" % (xian_shi, 100.0 * abs(a_zhi - b_zhi) / max(a_zhi, b_zhi, 1)))
        hang.append("- bpftrace 对账(同源探针): " + "; ".join(xiang))
    if "san_xing_zhen_ji_yan_shi" in mk:
        z = mk["san_xing_zhen_ji_yan_shi"]
        hang.append("- 三星真机演示: 断言 %s, 最快恢复 %s ms" %
                    (z["duan_yan"], z["zui_hao_hui_fu_ms"]))
    with open(SHU_CHU + ".md", "w") as f:
        f.write("\n".join(hang) + "\n")
    print("\n".join(hang))
    print("已写入 %s.json / %s.md" % (SHU_CHU, SHU_CHU))


if __name__ == "__main__":
    main()
