"""Create a minimal portable player ZIP; development sources stay on GitHub."""
import argparse
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parent

USAGE='''奶龙外卖 · 暨珠急送 — 解压即玩版

【开始游戏】
1. 把压缩包完整解压到一个可以写入的文件夹。
2. 打开“奶龙外卖”文件夹，双击“奶龙外卖.exe”。
3. 正常游玩不需要安装 Python，不需要联网。

适用 Windows 64 位电脑；此包已在 Windows 11 64 位测试。
请先解压再运行。移动或转发时保留整个文件夹，特别是“_internal”。
可以给“奶龙外卖.exe”创建自己的桌面快捷方式。

【怎么玩】
选择 4 单、6 单、8 单或自由模式，点击地点或订单选单，拖动右侧已选订单重排。
可以点“撤销”或 Ctrl+Z 退回上一步，长列表拖到边缘会自动滚动。
奶龙从食堂出发，按“出发”后开始送餐。自由模式可选择全部 29 个地点。
途中随机发生施工绕行、突然加急、饥饿补给和奶龙追逐，需要玩家参与操作。
事件期间配送自动暂停，做完选择后继续；结果按事件阶段公平比较路线成本。
4 单最多一次事件；6/8 单两次，先送两单再触发。奶龙会随事件挠头、冒汗、捂肚子或庆祝。
结算中可打开“路线回放”，同时看玩家和参考路线，标记绕路，支持暂停、倍速和上下段切换。
音乐和音效在右上角调节；没有音频设备也可以正常游戏。

空格：出发 / 继续   N：新一趟   F：配送加速   H：玩法说明
M：音乐开关   S：音效开关   1/2/3/4：切换难度 / 自由模式
Ctrl+Z：撤销安排；路线回放时空格暂停/播放，左右键切换阶段
ESC：关闭普通弹窗；无弹窗时退出。事件弹窗需要先完成选择。

【文件说明】
奶龙外卖.exe   游戏启动入口
_internal      运行环境、地图、奶龙、音乐等资源，请完整保留
data           首次运行自动生成，保存本机成绩、音量设置和临时文件
agent.md       给接手的开发者或 AI 助手看的项目说明

这个分享包以干净状态交付。每个人首次运行都会创建自己的存档。
完整源码、测试和打包工具统一放在 GitHub，本包仅供直接游玩。
开发请访问 https://github.com/aixuname/nailong-campus-delivery
'''

GUIDE='''# 奶龙外卖 · 暨珠急送：交接说明

这是 Windows 64 位本地 Pygame 游戏。完整解压后双击 `奶龙外卖.exe`，无需安装 Python 或联网。`_internal/` 是必需运行资源，不能删除或单独移动 exe。

本包只有程序、运行资源、使用说明和这一份 `agent.md`。首次运行会在程序旁创建 `data/`，用于本机成绩、设置和临时文件；更新时保留使用者已有的 `data/`。

## 获取源码

完整源码、测试与打包工具统一放在 GitHub：
https://github.com/aixuname/nailong-campus-delivery

下载仓库后阅读根目录 `agent.md` 和 `source/README.md`，从 `source/` 运行或开发。修改源码后需重新构建整个 exe 文件夹。

## 协作约束

- 接新需求先确认目标、范围、约束，给出方案并等待确认；简单读取可直接做。
- 保持本地桌面游戏形态；依赖、缓存、日志和构建文件均留在项目目录。
- 使用相对程序位置的资源与存档路径，不硬编码作者的盘符或用户名。
- 发布玩家包时只带 exe、完整 `_internal/`、使用说明和一份 `agent.md`；不混入源码、测试、个人存档或快捷方式。
- 保留 29 地点选单、拖动撤销、四种互动事件、音乐音效与分阶段评分及路线回放。
- 评分使用 Dijkstra 路径成本，阶段内至多 12 单精确优化，更多订单用启发式参考路线；事件前后分别比较，不用未来路况追溯评分。

验证发布包时，在独立解压目录运行 `奶龙外卖.exe --desktop-check`；它会生成测试用 `data/`，不要将该目录重新收入发布包。
'''

def create(runtime,stage,output):
    runtime=runtime.resolve();stage=stage.resolve();output=output.resolve()
    if not (runtime/'奶龙外卖.exe').is_file() or not (runtime/'_internal').is_dir():
        raise ValueError('Runtime folder must contain 奶龙外卖.exe and _internal/')
    if stage.exists() or output.exists() or output.with_suffix('.zip.partial').exists():
        raise FileExistsError('Use a new staging folder and output archive to preserve existing files')
    stage.mkdir(parents=True)
    shutil.copy2(runtime/'奶龙外卖.exe',stage/'奶龙外卖.exe')
    shutil.copytree(runtime/'_internal',stage/'_internal')
    (stage/'使用说明.txt').write_text(USAGE,encoding='utf-8-sig')
    (stage/'agent.md').write_text(GUIDE,encoding='utf-8')
    # Empty local state is deliberately created on first launch, not copied.
    output.parent.mkdir(parents=True,exist_ok=True)
    partial=output.with_suffix('.zip.partial')
    with zipfile.ZipFile(partial,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(stage.rglob('*')):
            if path.is_file():
                archive.write(path,Path('奶龙外卖')/path.relative_to(stage))
    partial.replace(output)
    print(f'Archive: {output}\nSize: {output.stat().st_size/1024/1024:.1f} MB')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--runtime',required=True,type=Path)
    parser.add_argument('--stage',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    create(args.runtime,args.stage,args.output)
