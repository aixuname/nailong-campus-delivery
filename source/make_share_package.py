"""Create a clean portable game ZIP with sources and an agent handoff guide."""
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
source         Python 完整源码；只想玩游戏无需打开或安装任何开发工具
agent.md       给接手的开发者或 AI 助手看的项目说明
AGENTS.md      同一份指引，供支持该文件名的编码助手自动读取

这个分享包以干净状态交付。每个人首次运行都会创建自己的存档。
源码改动后需要重新打包才能更新 exe；详细方法见 agent.md 和 source/README.md。
'''

GUIDE='''# 奶龙外卖 · 暨珠急送：开发者与 Agent 指引

## 先启动

这是一个 Windows 64 位本地桌面小游戏，不是网站。完整解压后，双击项目根目录的 `奶龙外卖.exe` 即可离线游玩；运行时不需要 Python。保留 `_internal/`。资源和存档路径均相对程序位置计算，没有依赖原作者的盘符、用户名或开发目录。

根目录 `agent.md` 与 `AGENTS.md` 内容相同。Python 源码位于 `source/`，修改源码不会自动修改已编译的 exe。

## 协作与文件约束

- 接到新需求先确认目标、范围、约束，再给简洁方案并等待确认；简单明确的读取和排错可直接做。
- 保持本地桌面游戏形态，除非用户明确要求改成其他平台。
- 新增素材、数据、临时文件、日志、依赖和构建缓存均放在本项目目录内，不写全局 Python 环境或项目外配置。
- 不硬编码原作者的盘符或用户名；应用数据使用 `app_paths.APP_DIR / "data"`，资源使用 `app_paths.ASSET_DIR`。
- 保留收件人已有的 `data/`。分享发布包以干净状态交付；不要混入本机成绩、音量偏好、QA 输出或绝对路径快捷方式。
- 原始角色参考图保持原样；角色动画和图案在 Pygame 中实时绘制。音乐在本地生成，无联网运行依赖。

## 项目结构

| 路径 | 职责 |
| --- | --- |
| `source/main.py` | Pygame 窗口、输入、配送动画、主流程和结算 |
| `source/world.py` | 根据校园参考图重绘的路网和 29 个地点 |
| `source/engine.py` | Dijkstra、Held–Karp、贪心与 2-opt |
| `source/incidents.py` | 四种互动事件、重排恢复和分段成本记录 |
| `source/experience.py` | 拖动排序、撤销、逐段双路线回放和绕路解释 |
| `source/visuals.py` | 清晰地图、角色动画、事件图案、对话气泡 |
| `source/audio.py` | 原创配乐、7 种音效、音量和静音设置 |
| `source/app_paths.py` | 源码运行与打包运行的相对路径 |
| `source/assets/` | 奶龙参考图、WAV、图标和导出的地图 |
| `source/desktop_check.py` | 验证最终 exe 自带资源和完整游戏流程 |
| `source/test_game.py` | 算法、地图点击、动画、音频和基本流程检查 |
| `source/test_incidents.py` | 事件操作、评分、暂停恢复和随机完整局检查 |
| `source/test_experience.py` | 缩放窗口拖动、撤销边界、节奏和回放只读检查 |
| `source/build_desktop.py` | 生成免安装 exe 文件夹 |

## 保留的玩法

奶龙从食堂出发；4/6/8 单随机挑战和自由选点；29 个具名地点均可选。送完最后一单结束，不要求返回。经过其他订单点不自动送达，按玩家指定顺序交付。食堂在自由模式可作为途中补给地点。

已选订单可拖动重排，长列表支持拖动到边缘自动滚动；“撤销”和 Ctrl+Z 可撤销选单、清空或重排。施工重排保留已送达订单，历史不可跨越出发或事件边界。

配送途中 1～2 单不触发，3～5 单在两单后触发一次，6 单以上触发两次，至少先送两单，事件间至少间隔两次配送。事件在送达一站后触发，使当前位置是确定节点：

1. **施工**：封闭原路线上的一条可绕行道路，保留已交付订单，允许重排剩余任务，保证所有地点可达。
2. **加急**：新订单可插入任意剩余位置；全地点已选时升级一个现有订单。两站内送达可获独立徽章。
3. **饥饿**：选择食堂或小卖部作为强制下一站补给，补给不会误完成原订单。
4. **捣蛋奶龙**：12 秒内在地图点中三次，拿回餐袋获徽章；失败时自动归还，仍能继续。

规划阶段另有奶龙探头彩蛋。徽章、规划用时与路线评分独立。角色包含呼吸、歪头、眨眼、接单起跳、蹦跳配送、摆动餐包和送达庆祝。M/S 控制音乐/音效，空格出发或恢复，N 新一趟，F 加速，H 帮助。

角色会随事件挠头、冒汗、捂肚子或得意庆祝。结算的“路线回放”逐阶段同时播放实际和参考路线，标出实际额外经过的路段，解释成本差与首个不同的顺序。支持暂停、1/2 倍速、切换阶段和重播；回放只读，不可影响成本、徽章和存档。

## 评分约束

每段路按当时路况用 Dijkstra 求最低成本。每次途中事件前后分段记账；只比较该阶段的起点、实际完成的任务和当时路况，禁止用后来封路追溯修改已经走过的路程。

阶段内至多 12 单用 Held–Karp 精确优化，更多订单用多起点贪心与 2-opt，并明确写“参考优选”，不承诺全局最优。补给阶段需要比较“先食堂”和“先小卖部”的后续总成本。得分为各阶段参考成本之和除以实际成本之和乘 100，四舍五入且上限 100；两项都为零时记 100 分。该评分不是预知未来事件的整局全局最优解。

## 开发、测试与重新打包

详见 `source/README.md`。建议使用 Windows 64 位 Python 3.13；正常玩家不需要这些工具。

1. 进入 `source/`，运行 `安装依赖.bat`，只把 pygame 安装进项目内 `vendor/`。
2. 运行 `启动游戏.bat` 调试源码。
3. 运行 `运行检查.bat`，检查算法、桌面操作和所有事件。
4. 运行 `安装打包工具.bat`，工具安装到项目内 `.packaging/`。
5. 运行 `重新打包.bat`，产物在 `source/.build/dist/奶龙外卖/`。把整个产物文件夹发布，禁止只发送 exe。

不要默认覆盖正在使用的程序。保留收件人的 data，明确目标目录后替换程序和随包资源。新分享包可以用 `make_share_package.py --runtime <完整产物目录> --stage <项目内空目录> --output <zip路径>` 生成。

最终 exe 可通过 `奶龙外卖.exe --desktop-check` 做隐藏窗口自检；报告和测试成绩写入该 exe 旁的 data，发布前清理这些测试输出。分享包已在不同解压目录运行此检查，验证 29 个地点、音乐和四种事件。
'''

SOURCE_README='''# 源码开发说明

直接玩游戏请返回上级目录，双击“奶龙外卖.exe”。本目录供继续修改游戏使用。

## 源码运行

建议 Windows 64 位 Python 3.13。先双击“安装依赖.bat”，再双击“启动游戏.bat”。依赖只装到本目录 vendor/，临时文件和缓存位于本目录 data/。

双击“运行检查.bat”验证算法、桌面流程、四种事件、拖动撤销与路线回放。日志和 QA 截图留在本目录。

## 重新打包

1. 双击“安装打包工具.bat”，只安装到本目录 .packaging/。
2. 双击“重新打包.bat”。
3. 结果位于 .build/dist/奶龙外卖/，包含 exe 和 _internal/，完整复制给使用者。

构建临时文件、缓存和中间产物均位于 .build/。不要把正在运行的原版本直接覆盖。主压缩包里的 exe 是发布快照，源码修改后需重新构建才会生效。

## 进一步说明

详见上级目录 agent.md。地图为示意图，距离为游戏内相对单位；随机事件按阶段比较评分，徽章独立。游戏运行不请求网络，不需要账号。
'''

def bat(body):
    header='''@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist "data\\temp" mkdir "data\\temp"
set "TEMP=%~dp0data\\temp"
set "TMP=%TEMP%"
set "PYTHONDONTWRITEBYTECODE=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_CACHE_DIR=%~dp0data\\pip-cache"
set "PYTHON_EXE="
set "PYTHON_FLAGS="
where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_EXE=py"
  set "PYTHON_FLAGS=-3"
) else (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON_EXE=python"
)
if not defined PYTHON_EXE (
  echo 未找到 Python。只想玩游戏请返回上级目录打开“奶龙外卖.exe”。
  echo 修改源码需要安装 Windows 64 位 Python，建议 3.13。
  pause
  exit /b 1
)
'''
    return (header+body+'\nendlocal\n').replace('\n','\r\n')

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
    (stage/'AGENTS.md').write_text(GUIDE,encoding='utf-8')
    source=stage/'source';source.mkdir()
    for path in ROOT.glob('*.py'):
        shutil.copy2(path,source/path.name)
    shutil.copytree(ROOT/'assets',source/'assets')
    shutil.copy2(ROOT/'requirements.txt',source/'requirements.txt')
    (source/'requirements-build.txt').write_text('pyinstaller==6.22.3\nsetuptools==80.10.2\npygame==2.6.1\n',encoding='utf-8')
    (source/'README.md').write_text(SOURCE_README,encoding='utf-8')
    scripts={
        '启动游戏.bat':'"%PYTHON_EXE%" %PYTHON_FLAGS% -B main.py\nif errorlevel 1 pause\n',
        '安装依赖.bat':'"%PYTHON_EXE%" %PYTHON_FLAGS% -B -m pip install --target "%~dp0vendor" --cache-dir "%PIP_CACHE_DIR%" --only-binary=:all: -r requirements.txt\nif errorlevel 1 (echo 安装失败。) else (echo 安装完成，可启动源码版。)\npause\n',
        '安装打包工具.bat':'"%PYTHON_EXE%" %PYTHON_FLAGS% -B -m pip install --target "%~dp0.packaging" --cache-dir "%PIP_CACHE_DIR%" --only-binary=:all: -r requirements-build.txt\nif errorlevel 1 (echo 安装失败。) else (echo 安装完成，可运行重新打包.bat。)\npause\n',
        '重新打包.bat':'"%PYTHON_EXE%" %PYTHON_FLAGS% -B build_desktop.py\nif errorlevel 1 (echo 构建失败。) else (echo 构建完成，查看 .build\\dist\\奶龙外卖 文件夹。)\npause\n',
        '运行检查.bat':'"%PYTHON_EXE%" %PYTHON_FLAGS% -B test_game.py\nif errorlevel 1 (pause & exit /b 1)\n"%PYTHON_EXE%" %PYTHON_FLAGS% -B test_incidents.py\nif errorlevel 1 (pause & exit /b 1)\n"%PYTHON_EXE%" %PYTHON_FLAGS% -B test_experience.py\npause\n'
    }
    for name,body in scripts.items():
        (source/name).write_bytes(bat(body).encode('utf-8'))
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
