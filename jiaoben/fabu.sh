#!/bin/bash
# 生成"单提交"发布快照:把当前工作树(排除构建产物、虚拟环境、缓存)复制到一个独立目录,
# 做成全新的 git 仓库并只提交一次。原仓库的历史完全不动。
# 发布到 GitHub / Gitee 后,页面上只会显示这一个初始提交。
#
# 用法:
#   bash jiaoben/fabu.sh [目标目录]        # 缺省 ../yuanma-fabu
# 之后按脚本末尾打印的命令推送即可。
set -e

GEN="$(cd "$(dirname "$0")/.." && pwd)"
MU="${1:-$(dirname "$GEN")/yuanma-fabu}"

if [ -e "$MU" ]; then
    echo "目标目录已存在: $MU"
    echo "确认要重建就先删掉它: rm -rf '$MU'"
    exit 1
fi

mkdir -p "$MU"
rsync -a \
    --exclude='.git' --exclude='chengwu' --exclude='xingxin/xingxin' \
    --exclude='__pycache__' --exclude='.pytest_cache' --exclude='*.pyc' \
    --exclude='.shendu_venv' --exclude='*.bpf.o' --exclude='*.skel.h' \
    --exclude='DEMO.md' \
    "$GEN/" "$MU/"

cd "$MU"
git init -q -b main
git add -A
zz_name="${WX_FABU_NAME:-$(git -C "$GEN" config user.name || true)}"
zz_mail="${WX_FABU_MAIL:-$(git -C "$GEN" config user.email || true)}"
zz_msg="${WX_FABU_MSG:-低轨星座智能计算保障系统:星上 eBPF 观测、场景检测、星间自愈与云端调度}"
git -c user.name="${zz_name:-yuanma}" -c user.email="${zz_mail:-yuanma@example.com}" \
    commit -q -m "$zz_msg"

echo "=== 快照就绪: $MU ==="
git -C "$MU" log --oneline
echo "文件数: $(git -C "$MU" ls-files | wc -l) | 体积: $(du -sh --exclude=.git "$MU" | cut -f1)"
echo
echo "推送步骤(先在 Gitee / GitHub 各建一个空仓库,不要勾选初始化 README):"
echo "  cd $MU"
echo "  git remote add gitee  git@gitee.com:<用户名>/<仓库名>.git"
echo "  git remote add github git@github.com:<用户名>/<仓库名>.git"
echo "  git push -u gitee main && git push -u github main"
