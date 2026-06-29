# 球球大作战

基于 Python + Pygame 实现的「球球大作战 / Agar.io」风格单机小游戏。控制小球吃食物变大、分裂、吐球、躲避绿色病毒刺，并吞掉其他 Bot。

## 三个版本

| 文件 | 说明 |
| --- | --- |
| `球球大作战第一版本.py` | 基础版：核心玩法（移动 / 吃食物 / 分裂 / 吐球 / 病毒 / 大吃小）。 |
| `球球大作战第二版本.py` | 优化版：引入 `__slots__`、平方距离判定、修复输入法导致 W 键失效、鼠标左键吐球、修复合球除零。 |
| `球球大作战第三版本.py` | 完整版：开始菜单、小地图、空间哈希加速碰撞、可被喂满射出的飞行刺、四级优先级 Bot AI（病毒回避 / 逃跑 / 猎杀 / 觅食）、帧率无关的物理与相机。 |

推荐运行第三版本，功能最完整。

## 环境要求

- Python 3.10+
- Pygame（见 `requirements.txt`）

## 安装与运行

建议在虚拟环境中安装依赖：

```bash
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活虚拟环境
#    Windows (Git Bash / PowerShell):
venv/Scripts/activate
#    macOS / Linux:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行
python 球球大作战第三版本.py
```

## 操作说明

| 操作 | 按键 |
| --- | --- |
| 移动方向 | 移动鼠标 |
| 分裂 | 空格 `Space` |
| 吐球（第三版本） | 鼠标左键 |
| 吐球（第一/二版本） | `W` 键 或 鼠标左键 |
| 重生 / 开始 | `R` 键 或 鼠标右键 |

## 说明

- `venv/` 为本地虚拟环境，已在 `.gitignore` 中排除，不会上传到 GitHub；其他人 clone 后按上面的步骤用 `requirements.txt` 自行安装即可复现环境。
