#!/usr/bin/env python3
"""实验脚本共用的平台控制客户端。"""
import json
import socket

KONG_ZHI_DUAN = 8029


def fa_ming(ming, chaoshi=90):
    s = socket.create_connection(("127.0.0.1", 8029), timeout=chaoshi)
    s.settimeout(chaoshi)
    s.sendall((json.dumps(ming) + "\n").encode())
    shu = b""
    while True:
        kuai = s.recv(65536)
        if not kuai:
            break
        shu += kuai
        if b"\n" in shu:
            break
    s.close()
    return json.loads(shu.decode().strip().splitlines()[0])


def run(hao, line, expect="#", timeout=30):
    return fa_ming({"cmd": "run", "hao": hao, "line": line, "expect": expect, "timeout": timeout})


def xin_ri_zhui_jia(hao, jiu_daxiao):
    """读星间日志新增内容。"""
    try:
        with open("/tmp/qemu_env/share/shuju/xin%d.txt" % hao) as f:
            wen = f.read()
        return wen[jiu_daxiao:]
    except Exception:
        return ""


def ri_daxiao(hao):
    try:
        import os
        return os.path.getsize("/tmp/qemu_env/share/shuju/xin%d.txt" % hao)
    except Exception:
        return 0
