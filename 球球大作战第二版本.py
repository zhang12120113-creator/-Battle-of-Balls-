import pygame
import random
import math

SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
WORLD_SIZE = 4000
FPS = 60

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

font = None
font_ui = None

font_names = ['microsoftyahei', 'msyh', 'simhei', 'simsun', 'arialunicode', 'arial']
for name in font_names:
    try:
        font = pygame.font.SysFont(name, 18)
        font_ui = pygame.font.SysFont(name, 24)
        break
    except:
        continue

if font is None:
    try:
        font_path = r"C:\Windows\Fonts\msyh.ttc"
        font = pygame.font.Font(font_path, 18)
        font_ui = pygame.font.Font(font_path, 24)
    except:
        try:
            font_path = r"C:\Windows\Fonts\msyhbd.ttc"
            font = pygame.font.Font(font_path, 18)
            font_ui = pygame.font.Font(font_path, 24)
        except:
            font = pygame.font.Font(None, 18)
            font_ui = pygame.font.Font(None, 24)


def get_dist(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


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
        self.x += (avg_x - self.x) * 0.1
        self.y += (avg_y - self.y) * 0.1
        total_mass = sum(c.mass for c in player_cells)
        target_zoom = 1.0 / (total_mass ** 0.35) * 6.5
        target_zoom = max(0.2, min(1.5, target_zoom))
        self.zoom += (target_zoom - self.zoom) * 0.05

    def to_scr(self, x, y):
        return int((x - self.x) * self.zoom + SCREEN_WIDTH / 2), \
               int((y - self.y) * self.zoom + SCREEN_HEIGHT / 2)

    def s_rad(self, r):
        return max(2, int(r * self.zoom))


class EjectedMass:
    def __init__(self, x, y, angle, color, owner_cell):
        self.x = x
        self.y = y
        self.mass = 14
        self.radius = math.sqrt(self.mass) * 6
        self.color = color
        self.owner_cell = owner_cell
        speed = 35
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.friction = 0.88

    def move(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= self.friction
        self.vy *= self.friction
        self.x = max(self.radius, min(self.x, WORLD_SIZE - self.radius))
        self.y = max(self.radius, min(self.y, WORLD_SIZE - self.radius))

    def draw(self, surf, cam):
        sx, sy = cam.to_scr(self.x, self.y)
        sr = cam.s_rad(self.radius)
        if -sr < sx < SCREEN_WIDTH + sr and -sr < sy < SCREEN_HEIGHT + sr:
            pygame.draw.circle(surf, self.color, (sx, sy), sr)
            pygame.draw.circle(surf, (50, 50, 50), (sx, sy), sr, 1)


class Cell:
    def __init__(self, x, y, mass, color, name, is_bot=False):
        self.x = x
        self.y = y
        self.mass = mass
        self.color = color
        self.name = name
        self.is_bot = is_bot
        self.radius = 0
        self.update_rad()
        self.boost = 0
        self.boost_angle = 0
        self.merge_timer = 0
        self.shoot_delay = 0

    def update_rad(self):
        self.radius = math.sqrt(self.mass) * 6

    def move(self, mx, my):
        angle = math.atan2(my - self.y, mx - self.x)
        speed = 12 * (self.mass ** -0.4)
        speed = max(2, speed)
        if self.boost > 1:
            self.x += math.cos(self.boost_angle) * self.boost
            self.y += math.sin(self.boost_angle) * self.boost
            self.boost *= 0.85
        else:
            self.x += math.cos(angle) * speed
            self.y += math.sin(angle) * speed
        self.x = max(self.radius, min(self.x, WORLD_SIZE - self.radius))
        self.y = max(self.radius, min(self.y, WORLD_SIZE - self.radius))
        if self.merge_timer > 0:
            self.merge_timer -= 1
        if self.shoot_delay > 0:
            self.shoot_delay -= 1

    def split(self, mx, my):
        if self.mass < 35:
            return None
        new_mass = self.mass / 2
        self.mass = new_mass
        self.update_rad()
        angle = math.atan2(my - self.y, mx - self.x)
        dist = self.radius * 2
        new_cell = Cell(self.x + math.cos(angle) * dist,
                        self.y + math.sin(angle) * dist,
                        new_mass, self.color, self.name, self.is_bot)
        new_cell.boost = 40
        new_cell.boost_angle = angle
        cool = 600 + int(new_mass * 2)
        self.merge_timer = cool
        new_cell.merge_timer = cool
        return new_cell

    def eject(self, mx, my):
        if self.mass < 35 or self.shoot_delay > 0:
            return None
        self.mass -= 16
        self.update_rad()
        self.shoot_delay = 4
        angle = math.atan2(my - self.y, mx - self.x)
        spawn_dist = self.radius + 5
        ex = self.x + math.cos(angle) * spawn_dist
        ey = self.y + math.sin(angle) * spawn_dist
        return EjectedMass(ex, ey, angle, self.color, self)

    def draw(self, surf, cam):
        sx, sy = cam.to_scr(self.x, self.y)
        sr = cam.s_rad(self.radius)
        if -sr < sx < SCREEN_WIDTH + sr and -sr < sy < SCREEN_HEIGHT + sr:
            pygame.draw.circle(surf, self.color, (sx, sy), sr)
            pygame.draw.circle(surf, (255, 255, 255, 50), (sx - sr // 3, sy - sr // 3), sr // 3)
            if not self.is_bot or cam.zoom > 0.5:
                n_txt = font.render(self.name, True, (0, 0, 0))
                m_txt = font.render(str(int(self.mass)), True, (255, 255, 255))
                surf.blit(n_txt, (sx - n_txt.get_width() // 2, sy - sr // 2))
                surf.blit(m_txt, (sx - m_txt.get_width() // 2, sy + sr // 4))


def main():
    my_cells = [Cell(random.randint(500, 3500), random.randint(500, 3500),
                     200, (255, 50, 100), "张艺城大将军")]

    bots = [Cell(random.randint(0, WORLD_SIZE), random.randint(0, WORLD_SIZE),
                 random.randint(50, 150), random.choice(COLORS), f"Bot{i}", True)
            for i in range(20)]

    foods = [{"x": random.randint(0, WORLD_SIZE),
              "y": random.randint(0, WORLD_SIZE),
              "c": random.choice(COLORS)} for _ in range(800)]

    ejects = []
    viruses = [{"x": random.randint(100, WORLD_SIZE - 100),
                "y": random.randint(100, WORLD_SIZE - 100)} for _ in range(15)]

    cam = Camera()

    running = True
    while running:
        mx, my = pygame.mouse.get_pos()
        wmx = (mx - SCREEN_WIDTH / 2) / cam.zoom + cam.x
        wmy = (my - SCREEN_HEIGHT / 2) / cam.zoom + cam.y

        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    new_borns = []
                    if len(my_cells) < 16:
                        for c in my_cells:
                            if len(my_cells) + len(new_borns) >= 16:
                                break
                            res = c.split(wmx, wmy)
                            if res:
                                new_borns.append(res)
                    my_cells.extend(new_borns)

        if keys[pygame.K_w]:
            for c in my_cells:
                spore = c.eject(wmx, wmy)
                if spore:
                    ejects.append(spore)

        if not my_cells:
            if keys[pygame.K_r]:
                my_cells = [Cell(random.randint(500, 3500), random.randint(500, 3500),
                                 60, (255, 50, 100), "Hero")]

        cam.update(my_cells)

        for c in my_cells:
            c.move(wmx, wmy)

        for b in bots:
            if random.random() < 0.02:
                b.angle = random.uniform(0, 6.28)
            if not hasattr(b, 'angle'):
                b.angle = 0
            if b.x < 100 or b.x > WORLD_SIZE - 100:
                b.angle = 3.14 - b.angle
            if b.y < 100 or b.y > WORLD_SIZE - 100:
                b.angle = -b.angle
            tx = b.x + math.cos(b.angle) * 100
            ty = b.y + math.sin(b.angle) * 100
            b.move(tx, ty)

        for e in ejects:
            e.move()

        all_cells = my_cells + bots

        surviving_foods = []
        for f in foods:
            eaten = False
            for c in all_cells:
                if abs(c.x - f['x']) < c.radius and abs(c.y - f['y']) < c.radius:
                    c.mass += 1
                    c.update_rad()
                    eaten = True
                    break
            if not eaten:
                surviving_foods.append(f)
        foods = surviving_foods
        while len(foods) < 800:
            foods.append({"x": random.randint(0, WORLD_SIZE),
                          "y": random.randint(0, WORLD_SIZE),
                          "c": random.choice(COLORS)})

        surviving_ejects = []
        for e in ejects:
            eaten_by = None
            for c in all_cells:
                dist = get_dist(c, e)
                if dist < c.radius:
                    is_owner = (c == e.owner_cell)
                    can_eat = False
                    if not is_owner:
                        can_eat = True
                    elif is_owner and (abs(e.vx) < 1 and abs(e.vy) < 1):
                        can_eat = True
                    if can_eat:
                        c.mass += 14
                        c.update_rad()
                        eaten_by = c
                        break
            if not eaten_by:
                surviving_ejects.append(e)
        ejects = surviving_ejects

        if len(my_cells) > 1:
            i = 0
            while i < len(my_cells):
                j = i + 1
                while j < len(my_cells):
                    c1 = my_cells[i]
                    c2 = my_cells[j]
                    dist = get_dist(c1, c2)
                    if c1.merge_timer == 0 and c2.merge_timer == 0:
                        if dist < (c1.radius + c2.radius) * 0.4:
                            c1.mass += c2.mass
                            c1.update_rad()
                            my_cells.pop(j)
                            continue
                    else:
                        min_dist = c1.radius + c2.radius
                        if dist < min_dist:
                            overlap = min_dist - dist
                            if dist == 0:
                                dist = 1
                            dx = (c1.x - c2.x) / dist
                            dy = (c1.y - c2.y) / dist
                            force = 0.05
                            c1.x += dx * overlap * force
                            c1.y += dy * overlap * force
                            c2.x -= dx * overlap * force
                            c2.y -= dy * overlap * force
                    j += 1
                i += 1

        surviving_viruses = []
        for v in viruses:
            hit = False
            for c in all_cells:
                virus_obj = type('obj', (object,), {'x': v['x'], 'y': v['y']})
                if get_dist(c, virus_obj) < c.radius:
                    if c.mass > 130:
                        hit = True
                        c.mass += 100
                        parts = min(16, int(c.mass / 30))
                        if parts > 1:
                            m_per = c.mass / parts
                            c.mass = m_per
                            c.update_rad()
                            for _ in range(parts - 1):
                                ang = random.uniform(0, 6.28)
                                nc = Cell(c.x, c.y, m_per, c.color, c.name, c.is_bot)
                                nc.boost = 30
                                nc.boost_angle = ang
                                nc.merge_timer = 400
                                if c in my_cells and len(my_cells) < 16:
                                    my_cells.append(nc)
                                elif c in bots:
                                    bots.append(nc)
                        break
            if not hit:
                surviving_viruses.append(v)
            else:
                surviving_viruses.append({"x": random.randint(100, WORLD_SIZE - 100),
                                          "y": random.randint(100, WORLD_SIZE - 100)})
        viruses = surviving_viruses

        all_cells.sort(key=lambda x: x.mass, reverse=True)
        eaten_cells = set()
        for eater in all_cells:
            if eater in eaten_cells:
                continue
            for victim in all_cells:
                if eater == victim or victim in eaten_cells:
                    continue
                if eater.name == victim.name:
                    continue
                if eater.mass > victim.mass * 1.25 and get_dist(eater, victim) < eater.radius:
                    eater.mass += victim.mass
                    eater.update_rad()
                    eaten_cells.add(victim)

        my_cells = [c for c in my_cells if c not in eaten_cells]
        bots = [b for b in bots if b not in eaten_cells]
        while len(bots) < 20:
            bots.append(Cell(random.randint(0, WORLD_SIZE), random.randint(0, WORLD_SIZE),
                             random.randint(50, 150), random.choice(COLORS), "Bot"))

        screen.fill(BG_COLOR)

        grid_step = cam.s_rad(50 / cam.zoom * 2)
        if grid_step > 5:
            off_x = int(-cam.x * cam.zoom + SCREEN_WIDTH / 2) % grid_step
            off_y = int(-cam.y * cam.zoom + SCREEN_HEIGHT / 2) % grid_step
            for x in range(off_x, SCREEN_WIDTH, grid_step):
                pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, SCREEN_HEIGHT))
            for y in range(off_y, SCREEN_HEIGHT, grid_step):
                pygame.draw.line(screen, GRID_COLOR, (0, y), (SCREEN_WIDTH, y))

        for f in foods:
            sx, sy = cam.to_scr(f['x'], f['y'])
            if 0 < sx < SCREEN_WIDTH and 0 < sy < SCREEN_HEIGHT:
                pygame.draw.circle(screen, f['c'], (sx, sy), max(2, int(3 * cam.zoom)))

        for e in ejects:
            e.draw(screen, cam)

        for v in viruses:
            sx, sy = cam.to_scr(v['x'], v['y'])
            sr = cam.s_rad(45)
            if 0 < sx < SCREEN_WIDTH and 0 < sy < SCREEN_HEIGHT:
                pygame.draw.circle(screen, (50, 255, 50), (sx, sy), sr)
                pygame.draw.circle(screen, (40, 200, 40), (sx, sy), sr, 4)
                points = []
                for i in range(16):
                    r = sr if i % 2 == 0 else sr + 5
                    a = i * (6.28 / 16)
                    points.append((sx + math.cos(a) * r, sy + math.sin(a) * r))
                pygame.draw.polygon(screen, (40, 200, 40), points, 2)

        render_list = bots + my_cells
        render_list.sort(key=lambda x: x.mass)
        for c in render_list:
            c.draw(screen, cam)

        if my_cells:
            score = int(sum(c.mass for c in my_cells))
            txt = font_ui.render(f"总质量: {score} | 分身数: {len(my_cells)}/16", True, (50, 50, 50))
            screen.blit(txt, (20, 20))
            help_t = font.render("空格: 分裂     ", True, (100, 100, 100))
            screen.blit(help_t, (20, 50))
        else:
            center_txt = font_ui.render("游戏结束", True, (255, 50, 50))
            screen.blit(center_txt, (SCREEN_WIDTH // 2 - 140, SCREEN_HEIGHT // 2))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()