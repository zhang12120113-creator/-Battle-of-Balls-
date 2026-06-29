import pygame
import random
import math

SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
WORLD_SIZE = 4000
FPS = 60
# 颜色
COLORS = [
    (255, 107, 107), (78, 205, 196), (255, 230, 109), (26, 83, 92),
    (255, 46, 99), (8, 217, 214), (37, 42, 52), (255, 154, 162),
    (46, 204, 113), (155, 89, 182), (52, 152, 219), (241, 196, 15)
]
GRID_COLOR = (220, 220, 220)
BG_COLOR = (245, 245, 245)
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("球球大作战")
clock = pygame.time.Clock()
pygame.font.init()
# 字体初始化
font = font_ui = None
font_names = ['microsoftyahei', 'msyh', 'simhei', 'simsun', 'arialunicode', 'arial']
for name in font_names:
    try:
        font = pygame.font.SysFont(name, 18)
        font_ui = pygame.font.SysFont(name, 24)
        break
    except:
        continue
if font is None:
    for font_path in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc"]:
        try:
            font = pygame.font.Font(font_path, 18)
            font_ui = pygame.font.Font(font_path, 24)
            break
        except:
            continue
if font is None:
    font = pygame.font.Font(None, 18)
    font_ui = pygame.font.Font(None, 24)
# 病毒预计算角度
VIRUS_ANGLES = [(i * math.pi * 2 / 16) for i in range(16)]


def get_dist_sq(c1, c2):
    dx = c1.x - c2.x
    dy = c1.y - c2.y
    return dx * dx + dy * dy


class Food:
    __slots__ = ['x', 'y', 'c']

    def __init__(self, x, y, c):
        self.x = x
        self.y = y
        self.c = c


class Camera:
    def __init__(self):
        self.x = WORLD_SIZE / 2
        self.y = WORLD_SIZE / 2
        self.zoom = 1.0

    def update(self, player_cells):
        if not player_cells:
            return
        avg_x = sum(c.x for c in player_cells) / len(player_cells)
        avg_y = sum(c.y for c in player_cells) / len(player_cells)
        self.x += (avg_x - self.x) * 0.13
        self.y += (avg_y - self.y) * 0.13
        total_mass = sum(c.mass for c in player_cells)
        target_zoom = max(0.17, min(1.65, 7.0 / (total_mass ** 0.33)))
        self.zoom += (target_zoom - self.zoom) * 0.07

    def to_scr(self, x, y):
        return int((x - self.x) * self.zoom + SCREEN_WIDTH / 2), \
            int((y - self.y) * self.zoom + SCREEN_HEIGHT / 2)

    def s_rad(self, r):
        return max(2, int(r * self.zoom))


class EjectedMass:
    __slots__ = ['x', 'y', 'mass', 'radius', 'color', 'owner_cell', 'vx', 'vy', 'friction']

    def __init__(self, x, y, angle, color, owner_cell):
        self.x = x
        self.y = y
        self.mass = 10
        self.radius = math.sqrt(self.mass) * 7.2
        self.color = color
        self.owner_cell = owner_cell
        speed = 25
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.friction = 0.84

    def move(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= self.friction
        self.vy *= self.friction
        r = self.radius
        self.x = max(r, min(self.x, WORLD_SIZE - r))
        self.y = max(r, min(self.y, WORLD_SIZE - r))

    def draw(self, surf, cam):
        sx, sy = cam.to_scr(self.x, self.y)
        sr = cam.s_rad(self.radius)
        if -sr < sx < SCREEN_WIDTH + sr and -sr < sy < SCREEN_HEIGHT + sr:
            pygame.draw.circle(surf, self.color, (sx, sy), sr)
            pygame.draw.circle(surf, (30, 30, 30), (sx, sy), sr, 3)


class Cell:
    __slots__ = ['x', 'y', 'mass', 'color', 'name', 'is_bot', 'radius', 'boost', 'boost_angle', 'merge_timer',
                 'shoot_delay', 'angle', 'target']

    def __init__(self, x, y, mass, color, name, is_bot=False):
        self.x = x
        self.y = y
        self.mass = mass
        self.color = color
        self.name = name
        self.is_bot = is_bot
        self.radius = math.sqrt(mass) * 6
        self.boost = 0
        self.boost_angle = 0
        self.merge_timer = 0
        self.shoot_delay = 0
        self.angle = random.uniform(0, 6.28)
        self.target = None

    def update_rad(self):
        self.radius = math.sqrt(self.mass) * 6

    def move(self, target_x, target_y):
        if self.merge_timer > 0: self.merge_timer -= 1
        if self.shoot_delay > 0: self.shoot_delay -= 1
        if self.boost > 1:
            self.x += math.cos(self.boost_angle) * self.boost
            self.y += math.sin(self.boost_angle) * self.boost
            self.boost *= 0.83
        else:
            dx = target_x - self.x
            dy = target_y - self.y
            dist_sq = dx * dx + dy * dy
            if dist_sq > 0:
                dist = math.sqrt(dist_sq)
                angle = math.atan2(dy, dx)
                speed = max(1.4, 14.5 * (self.mass ** -0.42))
                self.x += math.cos(angle) * speed
                self.y += math.sin(angle) * speed
        r = self.radius
        self.x = max(r, min(self.x, WORLD_SIZE - r))
        self.y = max(r, min(self.y, WORLD_SIZE - r))

    def split(self, target_x, target_y, current_cell_count):
        if self.mass < 35 or current_cell_count >= 16:
            return None
        new_mass = self.mass / 2
        self.mass = new_mass
        self.update_rad()
        angle = math.atan2(target_y - self.y, target_x - self.x)
        dist = self.radius * 1.95
        new_cell = Cell(self.x + math.cos(angle) * dist,
                        self.y + math.sin(angle) * dist,
                        new_mass, self.color, self.name, self.is_bot)
        new_cell.boost = 45
        new_cell.boost_angle = angle
        cool = 550 + int(new_mass * 2.5)
        self.merge_timer = cool
        new_cell.merge_timer = cool
        return new_cell

    def eject(self, target_x, target_y):
        if self.mass < 32 or self.shoot_delay > 0:
            return None
        self.mass -= 10
        self.update_rad()
        self.shoot_delay = 2
        angle = math.atan2(target_y - self.y, target_x - self.x)
        spawn_dist = self.radius + 8
        ex = self.x + math.cos(angle) * spawn_dist
        ey = self.y + math.sin(angle) * spawn_dist
        return EjectedMass(ex, ey, angle, self.color, self)

    def draw(self, surf, cam):
        sx, sy = cam.to_scr(self.x, self.y)
        sr = cam.s_rad(self.radius)
        if -sr < sx < SCREEN_WIDTH + sr and -sr < sy < SCREEN_HEIGHT + sr:
            pygame.draw.circle(surf, self.color, (sx, sy), sr)
            pygame.draw.circle(surf, (255, 255, 255, 65), (sx - sr // 3, sy - sr // 3), max(1, sr // 3))
            pygame.draw.circle(surf, (30, 30, 30), (sx, sy), sr, 3)
            if not self.is_bot or cam.zoom > 0.5:
                n_txt = font.render(self.name, True, (0, 0, 0))
                m_txt = font.render(str(int(self.mass)), True, (255, 255, 255))
                surf.blit(n_txt, (sx - n_txt.get_width() // 2, sy - sr // 1.9))
                surf.blit(m_txt, (sx - m_txt.get_width() // 2, sy + sr // 3.8))


def main():
    my_cells = [Cell(random.randint(400, 3600), random.randint(400, 3600), 100, (255, 50, 100), "月")]
    bots = [Cell(random.randint(100, WORLD_SIZE - 100),
                 random.randint(100, WORLD_SIZE - 100),
                 random.randint(60, 170), random.choice(COLORS), f"Bot{i}", is_bot=True)
            for i in range(20)]
    foods = [Food(random.randint(50, WORLD_SIZE - 50),
                  random.randint(50, WORLD_SIZE - 50),
                  random.choice(COLORS)) for _ in range(800)]
    ejects = []
    viruses = [{"x": random.randint(120, WORLD_SIZE - 120),
                "y": random.randint(120, WORLD_SIZE - 120)} for _ in range(18)]
    cam = Camera()
    running = True
    while running:
        mx, my = pygame.mouse.get_pos()
        wmx = (mx - SCREEN_WIDTH / 2) / cam.zoom + cam.x
        wmy = (my - SCREEN_HEIGHT / 2) / cam.zoom + cam.y
        # ============= 核心输入修复 =============
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                # 空格分裂
                if event.key == pygame.K_SPACE:
                    new_borns = []
                    current_count = len(my_cells)
                    for c in my_cells[:]:
                        if current_count + len(new_borns) >= 16:
                            break
                        res = c.split(wmx, wmy, current_count + len(new_borns))
                        if res:
                            new_borns.append(res)
                    my_cells.extend(new_borns)
                # R键重生
                elif event.key == pygame.K_r:
                    if not my_cells:
                        my_cells = [Cell(random.randint(500, 3500), random.randint(500, 3500),
                                         100, (255, 50, 100), "月")]
            # 鼠标左键重生
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not my_cells:
                    my_cells = [Cell(random.randint(500, 3500), random.randint(500, 3500),
                                     100, (255, 50, 100), "月")]
        # 吐球：支持 W键 或 鼠标左键 (彻底解决输入法状态导致W键失效的问题)
        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed()
        if keys[pygame.K_w] or mouse_buttons[0]:
            for c in my_cells:
                spore = c.eject(wmx, wmy)
                if spore:
                    ejects.append(spore)
        cam.update(my_cells)
        # 玩家移动
        for c in my_cells:
            c.move(wmx, wmy)
        # 机器人AI
        for b in bots:
            if random.random() < 0.15 or b.target is None:
                closest = min(foods, key=lambda f: (b.x - f.x) ** 2 + (b.y - f.y) ** 2, default=None)
                if closest and ((b.x - closest.x) ** 2 + (b.y - closest.y) ** 2) < 650 ** 2:
                    b.target = closest
                else:
                    b.target = None
            if b.target:
                tx, ty = b.target.x, b.target.y
            else:
                tx = b.x + math.cos(b.angle) * 130
                ty = b.y + math.sin(b.angle) * 130
            if random.random() < 0.04:
                b.angle = random.uniform(0, 6.28)
            b.move(tx, ty)
        for e in ejects:
            e.move()
        all_cells = my_cells + bots
        # 吃食物
        surviving_foods = []
        for f in foods:
            eaten = False
            for c in all_cells:
                dx = c.x - f.x
                dy = c.y - f.y
                if dx * dx + dy * dy < (c.radius + 3) ** 2:
                    c.mass += 1
                    c.update_rad()
                    eaten = True
                    break
            if not eaten:
                surviving_foods.append(f)
        foods = surviving_foods
        while len(foods) < 800:
            foods.append(Food(random.randint(50, WORLD_SIZE - 50),
                              random.randint(50, WORLD_SIZE - 50),
                              random.choice(COLORS)))
        # 吃吐出的小球 (修复判定：必须依据真实半径)
        surviving_ejects = []
        for e in ejects:
            eaten_by = None
            for c in all_cells:
                dx = c.x - e.x
                dy = c.y - e.y
                # 碰撞判定优化：大球边缘触碰吐球边缘即可吃
                if dx * dx + dy * dy < (c.radius + e.radius - 5) ** 2:
                    is_owner = (c == e.owner_cell)
                    can_eat = not is_owner or (is_owner and abs(e.vx) < 2 and abs(e.vy) < 2)
                    if can_eat:
                        c.mass += 10
                        c.update_rad()
                        eaten_by = c
                        break
            if not eaten_by:
                surviving_ejects.append(e)
        ejects = surviving_ejects
        # 玩家细胞合并 (修复除零异常)
        if len(my_cells) > 1:
            merged = set()
            for i in range(len(my_cells)):
                if i in merged: continue
                for j in range(i + 1, len(my_cells)):
                    if j in merged: continue
                    c1, c2 = my_cells[i], my_cells[j]
                    dx = c1.x - c2.x
                    dy = c1.y - c2.y
                    dist_sq = dx * dx + dy * dy
                    rad_sum = c1.radius + c2.radius
                    if c1.merge_timer == 0 and c2.merge_timer == 0:
                        if dist_sq < (rad_sum * 0.37) ** 2:
                            c1.mass += c2.mass
                            c1.update_rad()
                            merged.add(j)
                    elif dist_sq < rad_sum * rad_sum:
                        if dist_sq == 0:  # 极端重叠防除零
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
        # 病毒 (修复判定：必须依据真实半径)
        surviving_viruses = []
        for v in viruses:
            hit = False
            for c in all_cells:
                dx = c.x - v['x']
                dy = c.y - v['y']
                # 碰到绿刺尖尖就炸，判定距离放宽
                if dx * dx + dy * dy < (c.radius + 40) ** 2 and c.mass > 135:
                    hit = True
                    parts = min(16, int(c.mass / 33))
                    if parts > 1:
                        m_per = c.mass / parts
                        c.mass = m_per
                        c.update_rad()
                        for _ in range(parts - 1):
                            ang = random.uniform(0, 6.28)
                            nc = Cell(c.x, c.y, m_per, c.color, c.name, c.is_bot)
                            nc.boost = 35
                            nc.boost_angle = ang
                            nc.merge_timer = 430
                            if c in my_cells and len(my_cells) < 16:
                                my_cells.append(nc)
                            elif c in bots:
                                bots.append(nc)
                    break
            if hit:
                surviving_viruses.append({"x": random.randint(120, WORLD_SIZE - 120),
                                          "y": random.randint(120, WORLD_SIZE - 120)})
            else:
                surviving_viruses.append(v)
        viruses = surviving_viruses
        # 大吃小
        all_cells.sort(key=lambda x: x.mass, reverse=True)
        eaten_cells = set()
        for eater in all_cells:
            if eater in eaten_cells: continue
            for victim in all_cells:
                if eater == victim or victim in eaten_cells or eater.name == victim.name:
                    continue
                dx = eater.x - victim.x
                dy = eater.y - victim.y
                if eater.mass > victim.mass * 1.25 and dx * dx + dy * dy < (eater.radius * 0.9) ** 2:
                    eater.mass += victim.mass
                    eater.update_rad()
                    eaten_cells.add(victim)
        my_cells = [c for c in my_cells if c not in eaten_cells]
        bots = [b for b in bots if b not in eaten_cells]
        while len(bots) < 20:
            bots.append(Cell(random.randint(100, WORLD_SIZE - 100),
                             random.randint(100, WORLD_SIZE - 100),
                             random.randint(60, 170), random.choice(COLORS), f"Bot{len(bots)}", True))
        # ====================== 绘图 ======================
        screen.fill(BG_COLOR)
        # 网格
        grid_step = cam.s_rad(55)
        if grid_step > 4:
            off_x = int(-cam.x * cam.zoom + SCREEN_WIDTH / 2) % grid_step
            off_y = int(-cam.y * cam.zoom + SCREEN_HEIGHT / 2) % grid_step
            for x in range(off_x, SCREEN_WIDTH, grid_step):
                pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, SCREEN_HEIGHT))
            for y in range(off_y, SCREEN_HEIGHT, grid_step):
                pygame.draw.line(screen, GRID_COLOR, (0, y), (SCREEN_WIDTH, y))
        # 食物
        for f in foods:
            sx, sy = cam.to_scr(f.x, f.y)
            if 0 < sx < SCREEN_WIDTH and 0 < sy < SCREEN_HEIGHT:
                pygame.draw.circle(screen, f.c, (sx, sy), max(2, int(3.6 * cam.zoom)))
        # 吐出的球
        for e in ejects:
            e.draw(screen, cam)
        # 病毒
        for v in viruses:
            sx, sy = cam.to_scr(v['x'], v['y'])
            sr = cam.s_rad(46)
            if 0 < sx < SCREEN_WIDTH and 0 < sy < SCREEN_HEIGHT:
                pygame.draw.circle(screen, (60, 255, 80), (sx, sy), sr)
                pygame.draw.circle(screen, (35, 200, 55), (sx, sy), sr, 5)
                points = [(sx + math.cos(a) * (sr if i % 2 == 0 else sr + 8),
                           sy + math.sin(a) * (sr if i % 2 == 0 else sr + 8))
                          for i, a in enumerate(VIRUS_ANGLES)]
                pygame.draw.polygon(screen, (35, 200, 55), points, 3)
        # 细胞
        render_list = bots + my_cells
        render_list.sort(key=lambda x: x.mass)
        for c in render_list:
            c.draw(screen, cam)
        # UI
        if my_cells:
            total_mass = int(sum(c.mass for c in my_cells))
            txt = font_ui.render(f"总质量: {total_mass}   分身: {len(my_cells)}/16", True, (40, 40, 40))
            screen.blit(txt, (25, 18))
            help_txt = font.render("空格:分裂 | W/鼠标左键:吐球 | R/鼠标左键:重生", True, (90, 90, 90))
            screen.blit(help_txt, (25, 52))
        else:
            over = font_ui.render("游戏结束！按 R 或 鼠标左键 重新开始", True, (255, 60, 60))
            screen.blit(over, (SCREEN_WIDTH // 2 - 210, SCREEN_HEIGHT // 2))
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    main()