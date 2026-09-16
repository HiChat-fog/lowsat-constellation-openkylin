#!/bin/bash
set -e

MING=${1:-weixing1}
IP=${2:-192.168.50.1}
LA=${3:-}
MU=/opt/weixing
RI=/var/log/weixing

if [ ! -f /mnt/share/agent_yonghu ]; then
    echo "请先挂载共享目录: mount -t 9p -o trans=virtio hostshare /mnt/share"
    exit 1
fi

systemctl stop agent.service xintiao.service jiance.service dianyuan.service 2>/dev/null || true
sleep 1

mkdir -p $MU $RI /etc/systemd/system
mkdir -p /etc/weixing
if [ ! -f /mnt/share/weixing.conf ] || ! grep -q '^miyao=' /mnt/share/weixing.conf 2>/dev/null; then
    touch /mnt/share/weixing.conf
    echo "miyao=$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')" >> /mnt/share/weixing.conf
    echo "ling_pai=$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')" >> /mnt/share/weixing.conf
fi
if [ -f /mnt/share/weixing.conf ]; then cp /mnt/share/weixing.conf /etc/weixing/weixing.conf; fi
rm -f $MU/agent_yonghu $MU/xingxin_riscv64 $MU/jiance $MU/jiankang $MU/dianyuan

cp /mnt/share/agent_yonghu /mnt/share/xingxin_riscv64 /mnt/share/jiance /mnt/share/jiankang /mnt/share/dianyuan $MU/
chmod +x $MU/*
mkdir -p $MU/renwu
cp /mnt/share/renwu_* $MU/renwu/ 2>/dev/null || true
if [ -f /mnt/share/dianyuan_jiankang.sh ]; then
    cp /mnt/share/dianyuan_jiankang.sh $MU/renwu/dianyuan_jiankang
    chmod +x $MU/renwu/dianyuan_jiankang
fi

SHU=/mnt/share/shuju
mkdir -p $SHU
if [ -w $SHU ]; then
    KU=$SHU/$MING.db
    SHUC=$SHU/$MING.json
else
    KU=$RI/weixing.db
    SHUC=$RI/agent.json
fi

cat > /etc/systemd/system/agent.service << EOF
[Unit]
Description=weixing guance agent
After=network.target
Wants=network.target
[Service]
Type=simple
ExecStart=$MU/agent_yonghu $MING 5 $KU
Restart=always
RestartSec=3
StandardOutput=append:$SHUC
StandardError=append:$RI/agent.log
[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/xintiao.service << EOF
[Unit]
Description=weixing xintiao
After=network.target
Wants=network.target
[Service]
Type=simple
Environment=IP=$IP
Environment=LA=$LA
Environment=WX_SHUJU=$SHU
Environment=WX_RENWU_MU=$MU/renwu
ExecStart=$MU/xingxin_riscv64 $MING 7946 \${IP} \${LA}
Nice=5
CPUQuota=70%
Restart=always
RestartSec=3
StandardOutput=append:$RI/xintiao.log
StandardError=append:$RI/xintiao.log
[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/dianyuan.service << DYEOF
[Unit]
Description=weixing dianyuan jiankang guanli
After=network.target
Wants=network.target
[Service]
Type=simple
ExecStart=$MU/dianyuan $MING
Restart=always
RestartSec=5
StandardOutput=append:$SHU/$MING.dianyuan
StandardError=append:$RI/dianyuan.log
[Install]
WantedBy=multi-user.target
DYEOF

cat > /etc/systemd/system/jiance.service << EOF
[Unit]
Description=weixing jiance
After=network.target
Wants=network.target
[Service]
Type=simple
ExecStart=$MU/jiance $MING
Restart=always
RestartSec=5
StandardOutput=append:$RI/jiance.log
StandardError=append:$RI/jiance.log
[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now agent.service xintiao.service jiance.service dianyuan.service

sleep 3
echo "=== 部署完成: $MING @ $IP ==="
systemctl is-active agent.service xintiao.service jiance.service dianyuan.service
echo "日志目录: $RI"