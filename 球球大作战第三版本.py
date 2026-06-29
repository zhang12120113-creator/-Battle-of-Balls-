import pygame
import random
import math

# ====================== 窗口与世界 ======================
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
WORLD_SIZE = 4000
FPS = 60

# ====================== 颜色 ======================
COLORS = [
    (255, 107, 107), (78, 205, 196), (255, 230, 109), (26, 83, 92),
    (255, 46, 99), (8, 217, 214), (37, 42, 52), (255, 154, 162),
    (46, 204, 113), (155, 89, 182), (52, 152, 219), (241, 196, 15)
]
GRID_COLOR = (220, 220, 220)
BG_COLOR = (245, 245, 245)

# ====================== 游戏常量 ======================
# 相机（视角跟随与缩放）
CAMERA_LERP_POS = 0.13
CAMERA_LERP_ZOOM = 0.07
CAMERA_ZOOM_MIN = 0.17
CAMERA_ZOOM_MAX = 1.65
CAMERA_ZOOM_SCALE = 7.0
CAMERA_ZOOM_EXP = 0.33

# 细胞（球体参数）
CELL_RADIUS_FACTOR = 6
CELL_MIN_SPEED = 1.4
CELL_SPEED_BASE = 14.5
CELL_SPEED_EXP = -0.42

# 分裂（空格触发）
SPLIT_MIN_MASS = 35
SPLIT_MAX_CELLS = 16
SPLIT_BOOST = 45
SPLIT_COOLDOWN_BASE = 550
SPLIT_COOLDOWN_MASS = 2.5

# 吐球（鼠标左键）
EJECT_COST = 10
EJECT_MIN_MASS = 32
EJECT_SPEED = 25
EJECT_FRICTION = 0.84
EJECT_RADIUS_FACTOR = 7.2
EJECT_DELAY = 2
BOOST_FRICTION = 0.83
PLAYER_DIR_LERP = 0.6    # 玩家方向平滑系数（比 Bot 的 0.12 更灵敏）
MAX_EJECTS = 200          # 弹射物数量上限
EJECT_MAX_LIFE = 900      # 弹射物最大存活帧数（15 秒 @ 60fps）

# 碰撞 / 合并
EAT_MASS_RATIO = 1.25
EAT_RANGE_FACTOR = 0.9
MERGE_OVERLAP = 0.37
PUSH_FACTOR = 0.09
MERGE_ATTRACT_RATIO = 0.65   # timer 剩余 65% 时开始吸引
MERGE_ATTRACT_FORCE = 0.06   # 吸引力基础系数

# 病毒（绿色刺状障碍物）
VIRUS_COUNT = 18
VIRUS_RADIUS = 46
# 已移除静态阈值，改为动态比较 cell.mass > virus.mass
VIRUS_BOOST = 35
VIRUS_MERGE_TIMER_MS = 7167   # 毫秒（原 430 帧 × 1000/60 ≈ 7167ms）
VIRUS_MIN_MASS_SPLIT = 33
VIRUS_BASE_MASS = 100          # 刺的默认内部质量
VIRUS_FRICTION = 0.90          # 刺被推动后的摩擦力衰减
VIRUS_PUSH_FORCE = 6           # 吐球推动刺的力度
VIRUS_FEEDS_TO_SHOOT = 7       # 喂几个球后射出
VIRUS_SHOOT_SPEED = 55         # 射出速度
VIRUS_PROJECTILE_LIFE = 300    # 飞行刺存活帧数（5秒）

# 食物 / Bot
FOOD_COUNT = 800
FOOD_MASS = 1
FOOD_VIS_RADIUS = 3.6
BOT_COUNT = 20
BOT_THINK_CHANCE = 0.15
BOT_WANDER_CHANCE = 0.04
BOT_VISION_RANGE = 650

# Bot AI 范围
BOT_FLEE_RANGE = 400
BOT_HUNT_RANGE = 500
BOT_HUNT_REEVAL = 0.10
BOT_VIRUS_AVOID_RANGE = 250       # Bot 病毒回避范围
BOT_PROJECTILE_AVOID_FRAMES = 15  # 飞行刺预警帧数
BOT_DIR_LERP = 0.12               # 方向平滑系数（越小越平滑）
BOT_WANDER_TURN_MAX = 0.35        # 游走时每帧最大转向（弧度，≈20°）

# 玩家
PLAYER_COLOR = (255, 50, 100)
PLAYER_NAME = "月"
PLAYER_START_MASS = 100
BOT_MIN_MASS = 60
BOT_MAX_MASS = 170

# 空间哈希
SPATIAL_CELL_SIZE = 250

# 小地图
MINIMAP_SIZE = 180
MINIMAP_MARGIN = 15

# ====================== Pygame 初始化 ======================
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("球球大作战")
clock = pygame.time.Clock()
pygame.font.init()

# 字体初始化：依次尝试系统字体 → 字体文件 → 默认字体
font = font_ui = font_title = None
font_names = ['microsoftyahei', 'msyh', 'simhei', 'simsun', 'arialunicode', 'arial']
for name in font_names:
    try:
        font = pygame.font.SysFont(name, 18)
        font_ui = pygame.font.SysFont(name, 24)
        font_title = pygame.font.SysFont(name, 64)
        break
    except Exception:
        continue
if font is None:
    for font_path in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc"]:
        try:
            font = pygame.font.Font(font_path, 18)
            font_ui = pygame.font.Font(font_path, 24)
            font_title = pygame.font.Font(font_path, 64)
            break
        except Exception:
            continue
if font is None:
    font = pygame.font.Font(None, 18)
    font_ui = pygame.font.Font(None, 24)
    font_title = pygame.font.Font(None, 64)

# 病毒星形绘制预计算（16 个顶点的 cos/sin）
VIRUS_ANGLES = [(i * math.pi * 2 / 16) for i in range(16)]
VIRUS_COS = [math.cos(a) for a in VIRUS_ANGLES]
VIRUS_SIN = [math.sin(a) for a in VIRUS_ANGLES]


# ====================== 空间哈希 ======================
class SpatialHash:
    """空间哈希网格，加速碰撞检测从 O(n²) 到近似 O(n)"""
    __slots__ = ['cell_size', 'grid']

    def __init__(self, cell_size=SPATIAL_CELL_SIZE):
        self.cell_size = cell_size
        self.grid = {}

    def clear(self):
        self.grid.clear()

    def _key(self, x, y):
        return int(x // self.cell_size), int(y // self.cell_size)

    def insert(self, obj, x, y, radius=0):
        """插入对象到覆盖其范围的所有网格单元"""
        min_kx = int((x - radius) // self.cell_size)
        max_kx = int((x + radius) // self.cell_size)
        min_ky = int((y - radius) // self.cell_size)
        max_ky = int((y + radius) // self.cell_size)
        for kx in range(min_kx, max_kx + 1):
            for ky in range(min_ky, max_ky + 1):
                key = (kx, ky)
                if key in self.grid:
                    self.grid[key].append(obj)
                else:
                    self.grid[key] = [obj]

    def query(self, x, y, radius=0):
        """查询范围内的所有对象（可能包含重复，调用者需去重）"""
        result = []
        min_kx = int((x - radius) // self.cell_size)
        max_kx = int((x + radius) // self.cell_size)
        min_ky = int((y - radius) // self.cell_size)
        max_ky = int((y + radius) // self.cell_size)
        for kx in range(min_kx, max_kx + 1):
            for ky in range(min_ky, max_ky + 1):
                bucket = self.grid.get((kx, ky))
                if bucket:
                    result.extend(bucket)
        return result


# ====================== 工具函数 ======================
def screen_to_world(mx, my, cam):
    return (mx - SCREEN_WIDTH / 2) / cam.zoom + cam.x, \
           (my - SCREEN_HEIGHT / 2) / cam.zoom + cam.y


def clamp_world(x, y, r):
    """将坐标钳制到世界边界内"""
    return max(r, min(x, WORLD_SIZE - r)), max(r, min(y, WORLD_SIZE - r))


# ====================== 游戏对象类 ======================
class Food:
    __slots__ = ['x', 'y', 'c', 'alive']

    def __init__(self, x, y, c):
        self.x = x
        self.y = y
        self.c = c
        self.alive = True


class Camera:
    def __init__(self):
        self.x = WORLD_SIZE / 2
        self.y = WORLD_SIZE / 2
        self.zoom = 1.0

    def update(self, player_cells, dt_ms=16.67):
        if not player_cells:
            return
        total_mass = sum(c.mass for c in player_cells)
        # 质量加权中心：大球对相机影响更大，合并时不会跳
        avg_x = sum(c.x * c.mass for c in player_cells) / total_mass
        avg_y = sum(c.y * c.mass for c in player_cells) / total_mass
            # 帧率无关 lerp（指数衰减模型），保证任意帧率下相机平滑度一致
        factor_pos = 1 - (1 - CAMERA_LERP_POS) ** (dt_ms / 16.67)
        factor_zoom = 1 - (1 - CAMERA_LERP_ZOOM) ** (dt_ms / 16.67)
        self.x += (avg_x - self.x) * factor_pos
        self.y += (avg_y - self.y) * factor_pos
        target_zoom = max(CAMERA_ZOOM_MIN, min(CAMERA_ZOOM_MAX,
                                                CAMERA_ZOOM_SCALE / (total_mass ** CAMERA_ZOOM_EXP)))
        self.zoom += (target_zoom - self.zoom) * factor_zoom

    def to_scr(self, x, y):
        return int((x - self.x) * self.zoom + SCREEN_WIDTH / 2), \
               int((y - self.y) * self.zoom + SCREEN_HEIGHT / 2)

    def s_rad(self, r):
        return max(2, int(r * self.zoom))


class EjectedMass:
    __slots__ = ['x', 'y', 'mass', 'radius', 'color', 'owner_cell', 'vx', 'vy', 'friction', 'life']

    def __init__(self, x, y, angle, color, owner_cell):
        self.x = x
        self.y = y
        self.mass = EJECT_COST
        self.radius = math.sqrt(self.mass) * EJECT_RADIUS_FACTOR
        self.color = color
        self.owner_cell = owner_cell
        self.vx = math.cos(angle) * EJECT_SPEED
        self.vy = math.sin(angle) * EJECT_SPEED
        self.friction = EJECT_FRICTION
        self.life = EJECT_MAX_LIFE

    def move(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= self.friction
        self.vy *= self.friction
        self.life -= 1
        r = self.radius
        self.x = max(r, min(self.x, WORLD_SIZE - r))
        self.y = max(r, min(self.y, WORLD_SIZE - r))

    def is_dead(self):
        """是否应该被移除（仅看生命周期，速度只影响能否被原主吃回）"""
        return self.life <= 0

    def draw(self, surf, cam):
        sx, sy = cam.to_scr(self.x, self.y)
        sr = cam.s_rad(self.radius)
        if -sr < sx < SCREEN_WIDTH + sr and -sr < sy < SCREEN_HEIGHT + sr:
            pygame.draw.circle(surf, self.color, (sx, sy), sr)
            pygame.draw.circle(surf, (30, 30, 30), (sx, sy), sr, 3)


class Virus:
    __slots__ = ['x', 'y', 'mass', 'vx', 'vy', 'feed_count', 'radius']

    def __init__(self, x=None, y=None):
        self.x = x if x is not None else random.randint(120, WORLD_SIZE - 120)
        self.y = y if y is not None else random.randint(120, WORLD_SIZE - 120)
        self.mass = VIRUS_BASE_MASS
        self.vx = 0.0
        self.vy = 0.0
        self.feed_count = 0
        self.radius = VIRUS_RADIUS

    def update(self):
        """每帧更新：应用摩擦力、移动、边界钳制"""
        self.vx *= VIRUS_FRICTION
        self.vy *= VIRUS_FRICTION
        if abs(self.vx) < 0.1:
            self.vx = 0
        if abs(self.vy) < 0.1:
            self.vy = 0
        self.x += self.vx
        self.y += self.vy
        self.x, self.y = clamp_world(self.x, self.y, self.radius)

    def absorb_eject(self, eject):
        """吸收一个吐球，增大自身并沿吐球方向推动。返回是否达到射出阈值"""
        self.mass += eject.mass
        self.feed_count += 1
        self.radius = VIRUS_RADIUS * (self.mass / VIRUS_BASE_MASS)
        # 沿吐球速度方向推动刺
        speed = math.sqrt(eject.vx * eject.vx + eject.vy * eject.vy)
        if speed > 0.1:
            nx = eject.vx / speed
            ny = eject.vy / speed
            self.vx += nx * VIRUS_PUSH_FORCE
            self.vy += ny * VIRUS_PUSH_FORCE
        return self.feed_count >= VIRUS_FEEDS_TO_SHOOT

    def reset(self):
        """重置刺到默认状态"""
        self.mass = VIRUS_BASE_MASS
        self.vx = 0
        self.vy = 0
        self.feed_count = 0
        self.radius = VIRUS_RADIUS

    def draw(self, surf, cam):
        sx, sy = cam.to_scr(self.x, self.y)
        sr = cam.s_rad(self.radius)
        if -sr < sx < SCREEN_WIDTH + sr and -sr < sy < SCREEN_HEIGHT + sr:
            pygame.draw.circle(surf, (60, 255, 80), (sx, sy), sr)
            pygame.draw.circle(surf, (35, 200, 55), (sx, sy), sr, 5)
            # 星形尖刺长度随半径缩放
            spike_len = max(8, int(sr * 0.17))
            points = [(sx + VIRUS_COS[i] * (sr if i % 2 == 0 else sr + spike_len),
                       sy + VIRUS_SIN[i] * (sr if i % 2 == 0 else sr + spike_len))
                      for i in range(16)]
            pygame.draw.polygon(surf, (35, 200, 55), points, 3)


class VirusProjectile:
    """被喂满后射出的飞行刺，击中细胞会触发分裂"""
    __slots__ = ['x', 'y', 'vx', 'vy', 'radius', 'life']

    def __init__(self, x, y, angle, speed=VIRUS_SHOOT_SPEED):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.radius = VIRUS_RADIUS
        self.life = VIRUS_PROJECTILE_LIFE

    def move(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.x, self.y = clamp_world(self.x, self.y, self.radius)

    def is_dead(self):
        return self.life <= 0

    def draw(self, surf, cam):
        sx, sy = cam.to_scr(self.x, self.y)
        sr = cam.s_rad(self.radius)
        if -sr < sx < SCREEN_WIDTH + sr and -sr < sy < SCREEN_HEIGHT + sr:
            pygame.draw.circle(surf, (60, 255, 80), (sx, sy), sr)
            pygame.draw.circle(surf, (35, 200, 55), (sx, sy), sr, 5)
            spike_len = max(8, int(sr * 0.17))
            points = [(sx + VIRUS_COS[i] * (sr if i % 2 == 0 else sr + spike_len),
                       sy + VIRUS_SIN[i] * (sr if i % 2 == 0 else sr + spike_len))
                      for i in range(16)]
            pygame.draw.polygon(surf, (35, 200, 55), points, 3)


class Cell:
    __slots__ = ['x', 'y', 'mass', 'color', 'name', 'is_bot', 'radius', 'boost', 'boost_angle',
                 'merge_timer', 'merge_timer_max', 'shoot_delay', 'angle', 'target',
                 'prev_x', 'prev_y', 'vx', 'vy']

    def __init__(self, x, y, mass, color, name, is_bot=False):
        self.x = x
        self.y = y
        self.mass = mass
        self.color = color
        self.name = name
        self.is_bot = is_bot
        self.radius = math.sqrt(mass) * CELL_RADIUS_FACTOR
        self.boost = 0
        self.boost_angle = 0
        self.merge_timer = 0
        self.merge_timer_max = 0
        self.shoot_delay = 0
        self.angle = random.uniform(0, 6.28)
        self.target = None
        self.prev_x = x  # 用于计算速度方向
        self.prev_y = y
        self.vx = 0.0
        self.vy = 0.0

    def update_rad(self):
        self.radius = math.sqrt(self.mass) * CELL_RADIUS_FACTOR

    def move(self, target_x, target_y, dt_ms=16.67):
        # 合并计时器使用毫秒
        if self.merge_timer > 0:
            self.merge_timer = max(0, self.merge_timer - dt_ms)
        if self.shoot_delay > 0:
            self.shoot_delay -= 1
        if self.boost > 1:
            self.x += math.cos(self.boost_angle) * self.boost
            self.y += math.sin(self.boost_angle) * self.boost
            self.boost *= BOOST_FRICTION
            # boost 阶段同步速度状态
            self.vx = math.cos(self.boost_angle) * self.boost * BOOST_FRICTION
            self.vy = math.sin(self.boost_angle) * self.boost * BOOST_FRICTION
        else:
            dx = target_x - self.x
            dy = target_y - self.y
            dist_sq = dx * dx + dy * dy
            if dist_sq > 0:
                dist = math.sqrt(dist_sq)
                speed = max(CELL_MIN_SPEED, CELL_SPEED_BASE * (self.mass ** CELL_SPEED_EXP))
                target_vx = (dx / dist) * speed
                target_vy = (dy / dist) * speed
                if self.is_bot:
                    # Bot 用 lerp 平滑方向，消除抖动
                    self.vx += (target_vx - self.vx) * BOT_DIR_LERP
                    self.vy += (target_vy - self.vy) * BOT_DIR_LERP
                else:
                    # 玩家也用 lerp 平滑，比 Bot 更灵敏，避免与合球力冲突抖动
                    self.vx += (target_vx - self.vx) * PLAYER_DIR_LERP
                    self.vy += (target_vy - self.vy) * PLAYER_DIR_LERP
                self.x += self.vx
                self.y += self.vy
        r = self.radius
        self.x = max(r, min(self.x, WORLD_SIZE - r))
        self.y = max(r, min(self.y, WORLD_SIZE - r))

    def split(self, target_x, target_y, current_cell_count):
        if self.mass < SPLIT_MIN_MASS or current_cell_count >= SPLIT_MAX_CELLS:
            return None
        new_mass = self.mass / 2
        self.mass = new_mass
        self.update_rad()
        angle = math.atan2(target_y - self.y, target_x - self.x)
        dist = self.radius * 1.95
        new_cell = Cell(self.x + math.cos(angle) * dist,
                        self.y + math.sin(angle) * dist,
                        new_mass, self.color, self.name, self.is_bot)
        new_cell.boost = SPLIT_BOOST
        new_cell.boost_angle = angle
        cool_ms = int(SPLIT_COOLDOWN_BASE + new_mass * SPLIT_COOLDOWN_MASS) * (1000 / 60)
        self.merge_timer = cool_ms
        self.merge_timer_max = cool_ms
        new_cell.merge_timer = cool_ms
        new_cell.merge_timer_max = cool_ms
        return new_cell

    def eject(self, target_x, target_y):
        if self.mass < EJECT_MIN_MASS or self.shoot_delay > 0:
            return None
        self.mass -= EJECT_COST
        self.update_rad()
        self.shoot_delay = EJECT_DELAY
        angle = math.atan2(target_y - self.y, target_x - self.x)
        spawn_dist = self.radius + 8
        ex = self.x + math.cos(angle) * spawn_dist
        ey = self.y + math.sin(angle) * spawn_dist
        return EjectedMass(ex, ey, angle, self.color, self)

    def draw(self, surf, cam):
        sx, sy = cam.to_scr(self.x, self.y)
        sr = cam.s_rad(self.radius)
        if -sr < sx < SCREEN_WIDTH + sr and -sr < sy < SCREEN_HEIGHT + sr:
            # 主体
            pygame.draw.circle(surf, self.color, (sx, sy), sr)
            # 高光
            highlight = tuple(min(255, ch + 80) for ch in self.color)
            pygame.draw.circle(surf, highlight, (sx - sr // 3, sy - sr // 3), max(1, sr // 3))
            # 边框
            pygame.draw.circle(surf, (30, 30, 30), (sx, sy), sr, 3)
            # 名字 / 质量
            if not self.is_bot or cam.zoom > 0.5:
                n_txt = font.render(self.name, True, (0, 0, 0))
                m_txt = font.render(str(int(self.mass)), True, (255, 255, 255))
                surf.blit(n_txt, (sx - n_txt.get_width() // 2, sy - sr // 1.9))
                surf.blit(m_txt, (sx - m_txt.get_width() // 2, sy + sr // 3.8))


# ====================== 游戏初始化 ======================
def init_game():
    my_cells = [Cell(random.randint(400, 3600), random.randint(400, 3600),
                      PLAYER_START_MASS, PLAYER_COLOR, PLAYER_NAME)]
    bots = [Cell(random.randint(100, WORLD_SIZE - 100),
                 random.randint(100, WORLD_SIZE - 100),
                 random.randint(BOT_MIN_MASS, BOT_MAX_MASS),
                 random.choice(COLORS), f"Bot{i}", is_bot=True)
            for i in range(BOT_COUNT)]
    foods = [Food(random.randint(50, WORLD_SIZE - 50),
                  random.randint(50, WORLD_SIZE - 50),
                  random.choice(COLORS)) for _ in range(FOOD_COUNT)]
    ejects = []
    viruses = [Virus() for _ in range(VIRUS_COUNT)]
    virus_projectiles = []
    cam = Camera()
    bot_counter = BOT_COUNT
    return my_cells, bots, foods, ejects, viruses, cam, bot_counter, virus_projectiles


# ====================== 事件处理 ======================
def handle_events(events, my_cells, wmx, wmy):
    """返回 (my_cells, running)"""
    for event in events:
        if event.type == pygame.QUIT:
            return my_cells, False
        if event.type == pygame.KEYDOWN:
            # 空格分裂
            if event.key == pygame.K_SPACE and my_cells:
                new_borns = []
                current_count = len(my_cells)
                for c in my_cells[:]:
                    if current_count + len(new_borns) >= SPLIT_MAX_CELLS:
                        break
                    res = c.split(wmx, wmy, current_count + len(new_borns))
                    if res:
                        new_borns.append(res)
                my_cells.extend(new_borns)
            # R键重生
            elif event.key == pygame.K_r:
                if not my_cells:
                    my_cells = [Cell(random.randint(500, 3500), random.randint(500, 3500),
                                     PLAYER_START_MASS, PLAYER_COLOR, PLAYER_NAME)]
        # 鼠标右键重生（仅在死亡时）
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if not my_cells:
                my_cells = [Cell(random.randint(500, 3500), random.randint(500, 3500),
                                 PLAYER_START_MASS, PLAYER_COLOR, PLAYER_NAME)]
    return my_cells, True


def handle_eject(my_cells, wmx, wmy, ejects):
    """返回新吐出的 EjectedMass 列表"""
    new_ejects = []
    mouse_buttons = pygame.mouse.get_pressed()
    if mouse_buttons[0]:   # 鼠标左键吐球
        for c in my_cells:
            spore = c.eject(wmx, wmy)
            if spore:
                new_ejects.append(spore)
    # 限制弹射物总数
    if len(ejects) + len(new_ejects) > MAX_EJECTS:
        # 保留最新的 MAX_EJECTS 个
        overflow = len(ejects) + len(new_ejects) - MAX_EJECTS
        ejects = ejects[overflow:]
    return new_ejects, ejects


# ====================== 更新逻辑 ======================
def update_player_movement(my_cells, wmx, wmy, dt_ms):
    """更新所有玩家细胞向鼠标位置移动"""
    for c in my_cells:
        c.prev_x = c.x
        c.prev_y = c.y
        c.move(wmx, wmy, dt_ms)


def update_bot_ai(bots, foods, all_cells, viruses, virus_projectiles, dt_ms):
    """四级优先级 Bot AI：病毒回避 → 逃跑 → 猎杀 → 觅食"""
    for b in bots:
        # 记录上一帧位置（用于预判逃跑）
        b.prev_x = b.x
        b.prev_y = b.y

        # --- 优先级 0：病毒回避 ---
        b_radius = b.radius
        b_speed = max(CELL_MIN_SPEED, CELL_SPEED_BASE * (b.mass ** CELL_SPEED_EXP))
        repel_x = 0.0
        repel_y = 0.0
        dodging = False

        # 静态刺：只在该刺实际能分裂 Bot 时才回避
        for v in viruses:
            if b.mass <= v.mass:
                continue
            collision_dist = b_radius + 40  # 与 check_virus_collision 一致
            avoid_range = max(BOT_VIRUS_AVOID_RANGE, collision_dist + b_radius * 3)
            dx = b.x - v.x
            dy = b.y - v.y
            dsq = dx * dx + dy * dy
            if dsq < avoid_range * avoid_range:
                dist = math.sqrt(dsq) if dsq > 0 else 0.1
                urgency = (avoid_range - dist) / avoid_range
                weight = urgency * urgency
                repel_x += (dx / dist) * weight
                repel_y += (dy / dist) * weight
                dodging = True

        # 飞行刺：任何球都可能被击中（无 mass 检查）
        for p in virus_projectiles:
            collision_dist = b_radius + p.radius
            closing_speed = VIRUS_SHOOT_SPEED + b_speed
            avoid_range = collision_dist + closing_speed * BOT_PROJECTILE_AVOID_FRAMES
            dx = b.x - p.x
            dy = b.y - p.y
            dsq = dx * dx + dy * dy
            if dsq < avoid_range * avoid_range:
                dist = math.sqrt(dsq) if dsq > 0 else 0.1
                perp_x = dx / dist
                perp_y = dy / dist
                p_speed = math.sqrt(p.vx * p.vx + p.vy * p.vy) or 1
                p_dir_x = p.vx / p_speed
                p_dir_y = p.vy / p_speed
                dot = perp_x * p_dir_x + perp_y * p_dir_y
                in_path = dot < -0.3 or dist < collision_dist * 2
                if in_path:
                    urgency = (avoid_range - dist) / avoid_range
                    weight = urgency * urgency * 3.0
                    repel_x += perp_x * weight
                    repel_y += perp_y * weight
                    dodging = True

        if dodging:
            r_dist = math.sqrt(repel_x * repel_x + repel_y * repel_y) or 1
            nx = repel_x / r_dist
            ny = repel_y / r_dist
            b.move(b.x + nx * 300, b.y + ny * 300, dt_ms)
            continue

        # --- 优先级 1：逃跑（预判式） ---
        flee_range_sq = BOT_FLEE_RANGE ** 2
        nearest_threat = None
        nearest_threat_dist_sq = flee_range_sq + 1
        for c in all_cells:
            if c.name == b.name:
                continue
            if c.mass > b.mass * EAT_MASS_RATIO:
                dx = b.x - c.x
                dy = b.y - c.y
                dsq = dx * dx + dy * dy
                if dsq < flee_range_sq and dsq < nearest_threat_dist_sq:
                    nearest_threat = c
                    nearest_threat_dist_sq = dsq
        if nearest_threat is not None:
            # 预判逃跑：基于威胁的速度方向预测未来位置，提前转向
            pred_x = nearest_threat.x + (nearest_threat.x - nearest_threat.prev_x) * 8
            pred_y = nearest_threat.y + (nearest_threat.y - nearest_threat.prev_y) * 8
            dx = b.x - pred_x
            dy = b.y - pred_y
            dist = math.sqrt(dx * dx + dy * dy) or 1
            tx = b.x + (dx / dist) * 300
            ty = b.y + (dy / dist) * 300
            b.move(tx, ty, dt_ms)
            continue

        # --- 优先级 2：猎杀（距离加权） ---
        if random.random() < BOT_HUNT_REEVAL:
            hunt_range_sq = BOT_HUNT_RANGE ** 2
            best_prey = None
            best_prey_score = 0
            for c in all_cells:
                if c.name == b.name:
                    continue
                if b.mass > c.mass * EAT_MASS_RATIO and c.mass > 20:
                    dx = b.x - c.x
                    dy = b.y - c.y
                    dsq = dx * dx + dy * dy
                    if dsq < hunt_range_sq:
                        # 距离加权评分：质量 / 距离
                        score = c.mass / (math.sqrt(dsq) + 1)
                        if score > best_prey_score:
                            best_prey = c
                            best_prey_score = score
            b.target = best_prey

        # 检查目标是否仍然有效
        if b.target is not None:
            if isinstance(b.target, Food) and not b.target.alive:
                b.target = None
            elif isinstance(b.target, Cell) and not hasattr(b.target, 'mass'):
                b.target = None

        if b.target is not None:
            b.move(b.target.x, b.target.y, dt_ms)
            continue

        # --- 优先级 3：觅食（找最近食物 / 随机游走）---
        if random.random() < BOT_THINK_CHANCE or b.target is None:
            closest = None
            closest_dist_sq = BOT_VISION_RANGE ** 2
            for f in foods:
                if not f.alive:
                    continue
                dx = b.x - f.x
                dy = b.y - f.y
                dsq = dx * dx + dy * dy
                if dsq < closest_dist_sq:
                    closest = f
                    closest_dist_sq = dsq
            b.target = closest

        if b.target:
            tx, ty = b.target.x, b.target.y
        else:
            if random.random() < BOT_WANDER_CHANCE:
                b.angle += random.uniform(-BOT_WANDER_TURN_MAX, BOT_WANDER_TURN_MAX)
            tx = b.x + math.cos(b.angle) * 130
            ty = b.y + math.sin(b.angle) * 130
        b.move(tx, ty, dt_ms)


def update_ejects(ejects):
    """更新所有弹射物的位置和摩擦衰减"""
    for e in ejects:
        e.move()


def update_viruses(viruses):
    """每帧更新所有刺的物理运动"""
    for v in viruses:
        v.update()


# ====================== 碰撞检测 ======================
def check_food_collision(foods, all_cells, spatial_hash):
    """使用空间哈希加速食物碰撞检测"""
    surviving = []
    for f in foods:
        eaten = False
        # 只查询食物附近的细胞
        nearby = spatial_hash.query(f.x, f.y, 80)
        for c in nearby:
            dx = c.x - f.x
            if abs(dx) > c.radius + 5:
                continue
            dy = c.y - f.y
            if abs(dy) > c.radius + 5:
                continue
            if dx * dx + dy * dy < (c.radius + 3) ** 2:
                c.mass += FOOD_MASS
                c.update_rad()
                eaten = True
                f.alive = False  # 标记食物已被吃掉
                break
        if not eaten:
            surviving.append(f)
    # 补充食物
    while len(surviving) < FOOD_COUNT:
        new_food = Food(random.randint(50, WORLD_SIZE - 50),
                        random.randint(50, WORLD_SIZE - 50),
                        random.choice(COLORS))
        surviving.append(new_food)
    return surviving


def check_eject_collision(ejects, all_cells, spatial_hash):
    """使用空间哈希加速弹射物碰撞检测"""
    surviving = []
    for e in ejects:
        if e.is_dead():
            continue
        eaten_by = None
        nearby = spatial_hash.query(e.x, e.y, e.radius + 100)
        for c in nearby:
            dx = c.x - e.x
            dy = c.y - e.y
            if dx * dx + dy * dy < (c.radius + e.radius - 5) ** 2:
                is_owner = (c == e.owner_cell)
                can_eat = not is_owner or (is_owner and abs(e.vx) < 2 and abs(e.vy) < 2)
                if can_eat:
                    c.mass += EJECT_COST
                    c.update_rad()
                    eaten_by = c
                    break
        if not eaten_by:
            surviving.append(e)
    return surviving


def check_eject_virus_collision(ejects, viruses, all_cells, virus_projectiles):
    """检测吐球与刺的碰撞：刺吸收吐球变大、被推动，喂满后射出飞行刺"""
    surviving = []
    for e in ejects:
        if e.is_dead():
            continue
        consumed = False
        for v in viruses:
            dx = e.x - v.x
            dy = e.y - v.y
            dist_sq = dx * dx + dy * dy
            if dist_sq < (e.radius + v.radius) ** 2:
                should_shoot = v.absorb_eject(e)
                consumed = True
                if should_shoot:
                    # 找最近的细胞作为射出目标
                    best_cell = None
                    best_dist_sq = 600 * 600  # 最远600距离
                    for c in all_cells:
                        cdx = c.x - v.x
                        cdy = c.y - v.y
                        cdsq = cdx * cdx + cdy * cdy
                        if cdsq < best_dist_sq:
                            best_cell = c
                            best_dist_sq = cdsq
                    if best_cell is not None:
                        angle = math.atan2(best_cell.y - v.y, best_cell.x - v.x)
                        virus_projectiles.append(
                            VirusProjectile(v.x, v.y, angle))
                    # 重置刺
                    v.reset()
                break
        if not consumed:
            surviving.append(e)
    return surviving, virus_projectiles


def check_cell_merge(my_cells, dt_ms=16.67):
    """检查玩家自身细胞间的合并（timer 归零 + 足够重叠）或推离"""
    if len(my_cells) <= 1:
        return my_cells
    merged = set()
    for i in range(len(my_cells)):
        if i in merged:
            continue
        for j in range(i + 1, len(my_cells)):
            if j in merged:
                continue
            c1, c2 = my_cells[i], my_cells[j]
            dx = c1.x - c2.x
            dy = c1.y - c2.y
            dist_sq = dx * dx + dy * dy
            rad_sum = c1.radius + c2.radius
            # 双方 timer 归零 → 满足重叠条件则合并
            if c1.merge_timer == 0 and c2.merge_timer == 0:
                if dist_sq < (rad_sum * 0.37) ** 2:
                    c1.mass += c2.mass
                    c1.update_rad()
                    merged.add(j)
            # 否则重叠时推离
            elif dist_sq < rad_sum * rad_sum:
                if dist_sq == 0:
                    angle = random.uniform(0, 6.28)
                    c1.x += math.cos(angle)
                    c1.y += math.sin(angle)
                else:
                    dist = math.sqrt(dist_sq)
                    overlap = rad_sum - dist
                    nx = dx / dist
                    ny = dy / dist
                    c1.x += nx * overlap * 0.09
                    c1.y += ny * overlap * 0.09
                    c2.x -= nx * overlap * 0.09
                    c2.y -= ny * overlap * 0.09
    if merged:
        my_cells = [c for idx, c in enumerate(my_cells) if idx not in merged]
    return my_cells


def check_virus_collision(viruses, my_cells, bots):
    surviving = []
    all_cells = my_cells + bots
    my_set = set(id(c) for c in my_cells)  # 用 id set 代替线性搜索
    for v in viruses:
        hit = False
        for c in all_cells:
            dx = c.x - v.x
            dy = c.y - v.y
            if dx * dx + dy * dy < (c.radius + 40) ** 2 and c.mass > v.mass:
                hit = True
                # 限制分裂数量不超过 SPLIT_MAX_CELLS
                is_player = id(c) in my_set
                current_count = len(my_cells) if is_player else len(
                    [b for b in bots if b.name == c.name])
                parts = min(SPLIT_MAX_CELLS, int(c.mass / VIRUS_MIN_MASS_SPLIT))
                remaining_slots = SPLIT_MAX_CELLS - current_count
                parts = min(parts, remaining_slots + 1)
                if parts > 1:
                    m_per = c.mass / parts
                    c.mass = m_per
                    c.update_rad()
                    c.merge_timer = VIRUS_MERGE_TIMER_MS
                    c.merge_timer_max = VIRUS_MERGE_TIMER_MS
                    for _ in range(parts - 1):
                        ang = random.uniform(0, 6.28)
                        nc = Cell(c.x, c.y, m_per, c.color, c.name, c.is_bot)
                        nc.boost = VIRUS_BOOST
                        nc.boost_angle = ang
                        nc.merge_timer = VIRUS_MERGE_TIMER_MS
                        nc.merge_timer_max = VIRUS_MERGE_TIMER_MS
                        # 分裂后边界钳制
                        nc.x, nc.y = clamp_world(nc.x, nc.y, nc.radius)
                        if is_player and len(my_cells) < SPLIT_MAX_CELLS:
                            my_cells.append(nc)
                        elif not is_player:
                            bots.append(nc)
                break
        if hit:
            surviving.append(Virus())
        else:
            surviving.append(v)
    return surviving, my_cells, bots


def check_projectile_collision(virus_projectiles, my_cells, bots):
    """检测飞行刺击中细胞，触发分裂"""
    surviving = []
    all_cells = my_cells + bots
    my_set = set(id(c) for c in my_cells)
    for p in virus_projectiles:
        hit = False
        for c in all_cells:
            dx = c.x - p.x
            dy = c.y - p.y
            if dx * dx + dy * dy < (c.radius + p.radius) ** 2:
                hit = True
                is_player = id(c) in my_set
                current_count = len(my_cells) if is_player else len(
                    [b for b in bots if b.name == c.name])
                parts = min(SPLIT_MAX_CELLS, int(c.mass / VIRUS_MIN_MASS_SPLIT))
                remaining_slots = SPLIT_MAX_CELLS - current_count
                parts = min(parts, remaining_slots + 1)
                if parts > 1:
                    m_per = c.mass / parts
                    c.mass = m_per
                    c.update_rad()
                    c.merge_timer = VIRUS_MERGE_TIMER_MS
                    c.merge_timer_max = VIRUS_MERGE_TIMER_MS
                    for _ in range(parts - 1):
                        ang = random.uniform(0, 6.28)
                        nc = Cell(c.x, c.y, m_per, c.color, c.name, c.is_bot)
                        nc.boost = VIRUS_BOOST
                        nc.boost_angle = ang
                        nc.merge_timer = VIRUS_MERGE_TIMER_MS
                        nc.merge_timer_max = VIRUS_MERGE_TIMER_MS
                        nc.x, nc.y = clamp_world(nc.x, nc.y, nc.radius)
                        if is_player and len(my_cells) < SPLIT_MAX_CELLS:
                            my_cells.append(nc)
                        elif not is_player:
                            bots.append(nc)
                break
        if not hit:
            surviving.append(p)
    return my_cells, bots, surviving


def check_cell_eating(my_cells, bots, spatial_hash):
    """大球吃小球：按质量降序处理，使用空间哈希加速近邻查询"""
    all_cells = my_cells + bots
    all_cells.sort(key=lambda x: x.mass, reverse=True)
    eaten_cells = set()
    for eater in all_cells:
        if id(eater) in eaten_cells:
            continue
        # 只查询附近的细胞
        nearby = spatial_hash.query(eater.x, eater.y, eater.radius * 2)
        for victim in nearby:
            if eater == victim or id(victim) in eaten_cells or eater.name == victim.name:
                continue
            dx = eater.x - victim.x
            dy = eater.y - victim.y
            if eater.mass > victim.mass * EAT_MASS_RATIO and \
               dx * dx + dy * dy < (eater.radius * EAT_RANGE_FACTOR) ** 2:
                eater.mass += victim.mass
                eater.update_rad()
                eaten_cells.add(id(victim))
    my_cells = [c for c in my_cells if id(c) not in eaten_cells]
    bots = [b for b in bots if id(b) not in eaten_cells]
    return my_cells, bots


# ====================== 绘制函数 ======================
def draw_grid(surf, cam):
    """绘制世界坐标网格线，缩放时无抖动"""
    # 世界坐标网格线，消除缩放抖动
    world_step = 55
    # 计算可见范围（世界坐标）
    left = cam.x - SCREEN_WIDTH / 2 / cam.zoom
    right = cam.x + SCREEN_WIDTH / 2 / cam.zoom
    top = cam.y - SCREEN_HEIGHT / 2 / cam.zoom
    bottom = cam.y + SCREEN_HEIGHT / 2 / cam.zoom

    start_x = int(left // world_step) * world_step
    start_y = int(top // world_step) * world_step

    screen_step_x = world_step * cam.zoom
    screen_step_y = world_step * cam.zoom
    if screen_step_x < 4:
        return

    x = start_x
    while x <= right:
        sx = int((x - cam.x) * cam.zoom + SCREEN_WIDTH / 2)
        pygame.draw.line(surf, GRID_COLOR, (sx, 0), (sx, SCREEN_HEIGHT))
        x += world_step

    y = start_y
    while y <= bottom:
        sy = int((y - cam.y) * cam.zoom + SCREEN_HEIGHT / 2)
        pygame.draw.line(surf, GRID_COLOR, (0, sy), (SCREEN_WIDTH, sy))
        y += world_step


def draw_foods(surf, cam, foods, tick_ms):
    """批量绘制食物，带脉动动画"""
    vis_r = FOOD_VIS_RADIUS * cam.zoom
    for f in foods:
        sx, sy = cam.to_scr(f.x, f.y)
        if 0 < sx < SCREEN_WIDTH and 0 < sy < SCREEN_HEIGHT:
            # 微妙脉动（用位置做相位偏移，避免逐个 sin）
            phase = (f.x * 7 + f.y * 13) & 0xFF
            pulse = 1.0 + 0.15 * math.sin(tick_ms * 0.003 + phase * 0.0245)
            r = max(2, int(vis_r * pulse))
            pygame.draw.circle(surf, f.c, (sx, sy), r)


def draw_viruses(surf, cam, viruses):
    """批量绘制所有病毒"""
    for v in viruses:
        v.draw(surf, cam)


def draw_all_cells(surf, cam, bots, my_cells):
    # 先画 Bot（小），再画玩家细胞（大在上），避免排序
    for c in bots:
        c.draw(surf, cam)
    for c in my_cells:
        c.draw(surf, cam)


def draw_ui(surf, my_cells, fps=0):
    """绘制 HUD（质量、分身数、操作提示）或死亡画面"""
    if my_cells:
        total_mass = int(sum(c.mass for c in my_cells))
        txt = font_ui.render(f"总质量: {total_mass}   分身: {len(my_cells)}/{SPLIT_MAX_CELLS}", True, (40, 40, 40))
        surf.blit(txt, (SCREEN_WIDTH - txt.get_width() - 25, 18))
        help_txt = font.render("空格:分裂 | 左键:吐球 | R/右键:重生", True, (90, 90, 90))
        surf.blit(help_txt, (SCREEN_WIDTH - help_txt.get_width() - 25, 52))
        if fps > 0:
            fps_txt = font.render(f"FPS: {fps:.0f}", True, (120, 120, 120))
            surf.blit(fps_txt, (SCREEN_WIDTH - fps_txt.get_width() - 25, 74))
    else:
        # 死亡画面（半透明遮罩 + 提示文字）
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 60))
        surf.blit(overlay, (0, 0))
        over = font_title.render("游戏结束！", True, (255, 60, 60))
        surf.blit(over, (SCREEN_WIDTH // 2 - over.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
        hint = font_ui.render("按 R 或 鼠标右键 重新开始", True, (255, 255, 255))
        surf.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT // 2 + 30))


# 小地图
def draw_minimap(surf, cam, my_cells, bots, viruses):
    mm_x = MINIMAP_MARGIN
    mm_y = MINIMAP_MARGIN
    scale = MINIMAP_SIZE / WORLD_SIZE

    # 半透明背景
    mm_surf = pygame.Surface((MINIMAP_SIZE, MINIMAP_SIZE), pygame.SRCALPHA)
    mm_surf.fill((0, 0, 0, 80))

    # 病毒（绿色小点，大小随喂食增长）
    for v in viruses:
        px = int(v.x * scale)
        py = int(v.y * scale)
        if 0 <= px < MINIMAP_SIZE and 0 <= py < MINIMAP_SIZE:
            r = max(2, int(v.radius * scale))
            pygame.draw.circle(mm_surf, (60, 200, 60), (px, py), r)

    # Bot（灰色小点）
    for b in bots:
        px = int(b.x * scale)
        py = int(b.y * scale)
        if 0 <= px < MINIMAP_SIZE and 0 <= py < MINIMAP_SIZE:
            pygame.draw.circle(mm_surf, (180, 180, 180), (px, py), 2)

    # 玩家（红色亮点）
    for c in my_cells:
        px = int(c.x * scale)
        py = int(c.y * scale)
        if 0 <= px < MINIMAP_SIZE and 0 <= py < MINIMAP_SIZE:
            pygame.draw.circle(mm_surf, PLAYER_COLOR, (px, py), 3)

    # 视口范围矩形
    vp_left = (cam.x - SCREEN_WIDTH / 2 / cam.zoom) * scale
    vp_top = (cam.y - SCREEN_HEIGHT / 2 / cam.zoom) * scale
    vp_w = (SCREEN_WIDTH / cam.zoom) * scale
    vp_h = (SCREEN_HEIGHT / cam.zoom) * scale
    vp_rect = pygame.Rect(int(vp_left), int(vp_top), int(vp_w), int(vp_h))
    vp_rect.clamp_ip(mm_surf.get_rect())
    pygame.draw.rect(mm_surf, (255, 255, 255), vp_rect, 1)

    surf.blit(mm_surf, (mm_x, mm_y))
    pygame.draw.rect(surf, (100, 100, 100), (mm_x, mm_y, MINIMAP_SIZE, MINIMAP_SIZE), 2)


def draw_menu(surf):
    """绘制开始菜单（标题 + 装饰彩球）"""
    surf.fill(BG_COLOR)
    # 标题
    title = font_title.render("球球大作战", True, (255, 60, 80))
    surf.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, SCREEN_HEIGHT // 3 - 40))
    # 副标题
    sub = font_ui.render("按 鼠标右键 或 空格 开始游戏", True, (80, 80, 80))
    surf.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, SCREEN_HEIGHT // 2))
    # 装饰彩球
    for i in range(8):
        x = 200 + i * 120
        y = SCREEN_HEIGHT // 2 + 130
        pygame.draw.circle(surf, COLORS[i % len(COLORS)], (x, y), 30 + i * 3)
        highlight = tuple(min(255, ch + 80) for ch in COLORS[i % len(COLORS)])
        pygame.draw.circle(surf, highlight, (x - 10, y - 10), max(1, (30 + i * 3) // 3))
        pygame.draw.circle(surf, (30, 30, 30), (x, y), 30 + i * 3, 3)
    pygame.display.flip()


# ====================== 主循环 ======================
def main():
    game_state = "menu"  # menu / playing
    my_cells, bots, foods, ejects, viruses, cam, bot_counter, virus_projectiles = [], [], [], [], [], Camera(), 0, []
    running = True
    spatial_hash = SpatialHash()

    while running:
        dt_ms = clock.get_time()  # 上一帧耗时（毫秒）
        if dt_ms <= 0:
            dt_ms = 16.67  # 首帧兜底，约等于 60fps

        # ---------- 菜单状态 ----------
        if game_state == "menu":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    my_cells, bots, foods, ejects, viruses, cam, bot_counter, virus_projectiles = init_game()
                    game_state = "playing"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    my_cells, bots, foods, ejects, viruses, cam, bot_counter, virus_projectiles = init_game()
                    game_state = "playing"
            if running:
                draw_menu(screen)
            clock.tick(FPS)
            continue

        # ---------- 游戏状态 ----------
        mx, my = pygame.mouse.get_pos()
        wmx, wmy = screen_to_world(mx, my, cam)

        my_cells, running = handle_events(pygame.event.get(), my_cells, wmx, wmy)
        if not running:
            break

        new_ejects, ejects = handle_eject(my_cells, wmx, wmy, ejects)
        ejects.extend(new_ejects)
        update_player_movement(my_cells, wmx, wmy, dt_ms)

        # 统一构建 all_cells
        all_cells = my_cells + bots

        # 构建空间哈希（用于碰撞检测）
        spatial_hash.clear()
        for c in all_cells:
            spatial_hash.insert(c, c.x, c.y, c.radius)

        update_bot_ai(bots, foods, all_cells, viruses, virus_projectiles, dt_ms)
        update_ejects(ejects)
        update_viruses(viruses)

        # 飞行刺移动
        for p in virus_projectiles:
            p.move()
        virus_projectiles = [p for p in virus_projectiles if not p.is_dead()]

        foods = check_food_collision(foods, all_cells, spatial_hash)
        ejects = check_eject_collision(ejects, all_cells, spatial_hash)
        ejects, virus_projectiles = check_eject_virus_collision(
            ejects, viruses, all_cells, virus_projectiles)
        my_cells = check_cell_merge(my_cells, dt_ms)
        viruses, my_cells, bots = check_virus_collision(viruses, my_cells, bots)
        my_cells, bots, virus_projectiles = check_projectile_collision(
            virus_projectiles, my_cells, bots)
        my_cells, bots = check_cell_eating(my_cells, bots, spatial_hash)

        # 相机在所有位置更新（移动+合球+碰撞）之后更新，避免相机慢一拍
        cam.update(my_cells, dt_ms)

        # 补充 Bot
        while len(bots) < BOT_COUNT:
            bots.append(Cell(random.randint(100, WORLD_SIZE - 100),
                             random.randint(100, WORLD_SIZE - 100),
                             random.randint(BOT_MIN_MASS, BOT_MAX_MASS),
                             random.choice(COLORS), f"Bot{bot_counter}", True))
            bot_counter += 1

        # ---------- 渲染 ----------
        screen.fill(BG_COLOR)
        tick_ms = pygame.time.get_ticks()
        draw_grid(screen, cam)
        draw_foods(screen, cam, foods, tick_ms)
        for e in ejects:
            e.draw(screen, cam)
        draw_viruses(screen, cam, viruses)
        for p in virus_projectiles:
            p.draw(screen, cam)
        draw_all_cells(screen, cam, bots, my_cells)
        draw_ui(screen, my_cells, clock.get_fps())
        draw_minimap(screen, cam, my_cells, bots, viruses)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
