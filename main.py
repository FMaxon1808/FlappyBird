import pygame
import random
import sys
import json
import os

pygame.init()
WIDTH, HEIGHT = 400, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("Arial", 20)

# Цвета радуги
RAINBOW_COLORS = [
    (255, 0, 0),     # Красный
    (255, 127, 0),   # Оранжевый
    (255, 255, 0),   # Жёлтый
    (0, 255, 0),     # Зелёный
    (0, 0, 255),     # Синий
    (75, 0, 130),    # Индиго
    (148, 0, 211),   # Фиолетовый
]

# Другие цвета
PIPE_COLOR = (0, 255, 0)
PIPE_DANGER_COLOR = (255, 0, 0)
COIN_COLOR = (255, 215, 0)
SHIELD_COLOR = (135, 206, 250)
MAGNET_COLOR = (255, 20, 147)
HEART_COLOR = (255, 0, 0)
ENEMY_COLOR = (139, 0, 0)
BG_COLORS = [(135, 206, 250), (250, 250, 210), (255, 140, 0), (25, 25, 112)]
SAVE_FILE = "savegame.json"
DIFFICULTIES = {
    "Лёгкая": {"pipe_speed": 3, "enemy_rate": 600},
    "Средняя": {"pipe_speed": 4, "enemy_rate": 400},
    "Сложная": {"pipe_speed": 5, "enemy_rate": 250},
}

# Функция для отрисовки текста
def draw_text(text, x, y, color=(0, 0, 0)):
    img = FONT.render(text, True, color)
    screen.blit(img, (x, y))

# Функция для отрисовки прогресса миссий
def draw_mission_progress(missions_manager):
    x = WIDTH - 230
    y = 30
    draw_text("Миссии:", x, y - 25)
    for m in missions_manager.missions:
        if not m["completed"]:
            if "монет" in m["description"]:
                current = missions_manager.coins_collected
            elif "труб" in m["description"]:
                current = missions_manager.pipes_passed
            elif "сердечка" in m["description"]:
                current = missions_manager.hearts_collected
            else:
                current = 0
            draw_text(f"{m['description']}: {current}/{m['target']}", x, y)
            y += 25
            
# Функция для отрисовки шкалы здоровья
def draw_health_bar(x, y, health, max_health=100, width=100, height=10):
    pygame.draw.rect(screen, (0, 0, 0), (x - 2, y - 2, width + 4, height + 4))  # рамка
    pygame.draw.rect(screen, (255, 0, 0), (x, y, width, height))  # фон красный
    green_width = int((health / max_health) * width)
    pygame.draw.rect(screen, (0, 255, 0), (x, y, green_width, height))  # зелёная часть

# Главное меню: ввод имени и выбор сложности
def main_menu():
    input_name = ""
    selected_difficulty = 1
    difficulties = list(DIFFICULTIES.keys())
    active_input = True

    while True:
        screen.fill((255, 255, 255))
        draw_text("Введите имя игрока:", 40, 30)
        pygame.draw.rect(screen, (200, 200, 200), (40, 60, 300, 30))
        draw_text(input_name or "___", 45, 65)

        draw_text("Выберите сложность:", 40, 120)
        for i, diff in enumerate(difficulties):
            color = (0, 0, 0) if i != selected_difficulty else (255, 0, 0)
            draw_text(f"{i+1}. {diff}", 60, 160 + i * 30, color)

        draw_text("Нажмите ENTER чтобы начать", 40, 280)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if active_input:
                    if event.key == pygame.K_RETURN:
                        if input_name.strip():
                            return input_name, difficulties[selected_difficulty]
                    elif event.key == pygame.K_BACKSPACE:
                        input_name = input_name[:-1]
                    elif len(input_name) < 12 and event.unicode.isprintable():
                        input_name += event.unicode
                if pygame.K_1 <= event.key <= pygame.K_3:
                    selected_difficulty = event.key - pygame.K_1

        pygame.display.flip()
        clock.tick(30)

# Экран выбора цвета перед стартом
def choose_color():
    selected = 2  # по умолчанию жёлтый
    while True:
        screen.fill((255, 255, 255))
        draw_text("Выберите цвет птицы (1–7):", 40, 30)
        for i, color in enumerate(RAINBOW_COLORS):
            rect = pygame.Rect(50 + i * 50, 100, 40, 40)
            pygame.draw.rect(screen, color, rect)
            # цифра выбора
            draw_text(str(i + 1), rect.x + 12, rect.y + 12)
        draw_text("Нажмите SPACE для старта", 40, 200)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if pygame.K_1 <= event.key <= pygame.K_7:
                    selected = event.key - pygame.K_1
                elif event.key == pygame.K_SPACE:
                    return RAINBOW_COLORS[selected]
        pygame.display.flip()
        clock.tick(30)

# Класс птицы
class Bird:
    def __init__(self, color):
        self.color = color
        self.x = 60
        self.y = HEIGHT // 2
        self.vel = 0
        self.gravity = 0.5
        self.jump_power_base = -9
        self.jump_power = self.jump_power_base
        self.width = 40
        self.height = 30
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.lives = 3
        self.shield = False
        self.shield_duration = 0
        self.score = 0
        self.coins = 0
        self.immunity = 0
        self.health = 100
        self.rage_mode = False
        self.rage_timer = 0
        self.magnet_duration = 0

    def update(self):
        self.vel += self.gravity
        self.y += self.vel
        self.rect.y = int(self.y)
        # Таймер иммунитета
        if self.immunity > 0:
            self.immunity -= 1
        # Режим ярости
        if self.rage_mode:
            self.rage_timer -= 1
            if self.rage_timer <= 0:
                self.rage_mode = False
                self.health = 100
        # Щит
        if self.shield:
            self.shield_duration -= 1
            if self.shield_duration <= 0:
                self.shield = False
        # Магнит
        if self.magnet_duration > 0:
            self.magnet_duration -= 1

    def jump(self):
        self.vel = self.jump_power

    def draw(self):
        color = (255, 100, 100) if self.immunity > 0 else self.color
        if self.rage_mode:
            color = (255, 50, 50)
        pygame.draw.rect(screen, color, self.rect)
        if self.shield:
            pygame.draw.rect(screen, SHIELD_COLOR, self.rect.inflate(10, 10), 2)
        if self.magnet_duration > 0:
            pygame.draw.circle(screen, MAGNET_COLOR, self.rect.center, 50, 2)


class Pipe:
    def __init__(self, x):
        self.x = x
        self.width = 70
        self.gap = 150
        self.top = random.randint(60, HEIGHT - 220)
        self.bottom = self.top + self.gap
        self.rect_top = pygame.Rect(self.x, 0, self.width, self.top)
        self.rect_bottom = pygame.Rect(self.x, self.bottom, self.width, HEIGHT)
        self.scored = False
        self.danger = random.random() < 0.2

    def update(self, speed):
        self.x -= speed
        self.rect_top.x = self.rect_bottom.x = self.x

    def draw(self):
        color = PIPE_DANGER_COLOR if self.danger else PIPE_COLOR
        pygame.draw.rect(screen, color, self.rect_top)
        pygame.draw.rect(screen, color, self.rect_bottom)

class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 25, 25)
        self.collected = False

    def update(self, speed):
        self.rect.x -= speed

    def draw(self):
        if not self.collected:
            pygame.draw.ellipse(screen, COIN_COLOR, self.rect)

class PowerUp:
    def __init__(self, x, y, kind):
        self.kind = kind
        self.rect = pygame.Rect(x, y, 25, 25)

    def update(self, speed):
        self.rect.x -= speed

    def draw(self):
        color = SHIELD_COLOR if self.kind == "shield" else MAGNET_COLOR
        pygame.draw.rect(screen, color, self.rect)

class Heart:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 30, 30)
        self.collected = False

    def update(self, speed):
        self.rect.x -= speed

    def draw(self):
        if not self.collected:
            pygame.draw.ellipse(screen, HEART_COLOR, self.rect)

class Enemy:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.speed = random.randint(2, 4)

    def update(self):
        self.rect.x -= self.speed

    def draw(self):
        pygame.draw.rect(screen, ENEMY_COLOR, self.rect)

# Менеджеры
class MissionsManager:
    def __init__(self, bird):
        self.bird = bird
        self.missions = [
            {"description": "Собери 10 монет", "target": 10, "completed": False},
            {"description": "Пройди 20 труб", "target": 20, "completed": False},
            {"description": "Собери 3 сердечка", "target": 3, "completed": False},
        ]
        self.coins_collected = 0
        self.pipes_passed = 0
        self.hearts_collected = 0

    def update(self):
        self.coins_collected = self.bird.coins
        self.pipes_passed = self.bird.score
        for m in self.missions:
            if not m["completed"]:
                if m["description"] == "Собери 10 монет" and self.coins_collected >= m["target"]:
                    m["completed"] = True
                    self.bird.coins += 10
                elif m["description"] == "Пройди 20 труб" and self.pipes_passed >= m["target"]:
                    m["completed"] = True
                    self.bird.coins += 15
                elif m["description"] == "Собери 3 сердечка" and self.hearts_collected >= m["target"]:
                    m["completed"] = True
                    self.bird.coins += 20

class ImprovementsManager:
    def __init__(self, bird):
        self.bird = bird
        self.improvements = {
            "magnet_duration": {"level": 1, "cost": 10},
            "shield_duration": {"level": 1, "cost": 10},
            "jump_power": {"level": 1, "cost": 15},
        }

    def buy(self, imp):
        if self.bird.coins >= self.improvements[imp]["cost"]:
            self.bird.coins -= self.improvements[imp]["cost"]
            self.improvements[imp]["level"] += 1
            self.improvements[imp]["cost"] += 10
            self.apply_improvements()

    def apply_improvements(self):
        self.bird.magnet_duration = self.improvements["magnet_duration"]["level"] * 300
        self.bird.shield_duration = self.improvements["shield_duration"]["level"] * 300
        lvl = self.improvements["jump_power"]["level"]
        self.bird.jump_power = self.bird.jump_power_base * (1 + 0.1 * (lvl - 1))

    def draw_menu(self):
        y = 50
        draw_text(f"Магнит (1): уровень {self.improvements['magnet_duration']['level']} — цена {self.improvements['magnet_duration']['cost']}", 50, y)
        y += 40
        draw_text(f"Щит (2): уровень {self.improvements['shield_duration']['level']} — цена {self.improvements['shield_duration']['cost']}", 50, y)
        y += 40
        draw_text(f"Сила прыжка (3): уровень {self.improvements['jump_power']['level']} — цена {self.improvements['jump_power']['cost']}", 50, y)

class Weather:
    def __init__(self):
        self.type = random.choice(["clear", "rain", "fog", "wind"])
        self.timer = 0

    def update(self):
        self.timer += 1
        if self.timer > 1800:
            self.timer = 0
            self.type = random.choice(["clear", "rain", "fog", "wind"])

    def apply_effect(self, bird):
        if self.type == "wind":
            pass

    def draw(self):
        if self.type == "rain":
            for _ in range(20):
                x,y = random.randint(0,WIDTH), random.randint(0,HEIGHT)
                pygame.draw.line(screen, (0,0,255), (x,y), (x,y+10), 1)
        elif self.type == "fog":
            fog = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
            fog.fill((200,200,200,100))
            screen.blit(fog, (0,0))
        elif self.type == "wind":
            draw_text("Ветер дует!", WIDTH - 120, 10, (0,0,255))

class SaveManager:
    def __init__(self, bird, missions_manager, improvements_manager):
        self.bird = bird
        self.missions_manager = missions_manager
        self.improvements_manager = improvements_manager

    def save(self):
        data = {
            "coins": self.bird.coins,
            "score": self.bird.score,
            "lives": self.bird.lives,
            "missions": [(m["description"], m["completed"]) for m in self.missions_manager.missions],
            "improvements": {k: v["level"] for k, v in self.improvements_manager.improvements.items()},
        }
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)

    def load(self):
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
            self.bird.coins = data.get("coins", 0)
            self.bird.score = data.get("score", 0)
            self.bird.lives = data.get("lives", 3)
            comp = dict(data.get("missions", []))
            for m in self.missions_manager.missions:
                m["completed"] = comp.get(m["description"], False)
            imp_lvls = data.get("improvements", {})
            for k, lvl in imp_lvls.items():
                if k in self.improvements_manager.improvements:
                    self.improvements_manager.improvements[k]["level"] = lvl
            self.improvements_manager.apply_improvements()

# Основная функция
def main():
    player_name, difficulty = main_menu()
    bird_color = choose_color()
    bird = Bird(bird_color)
    pipes = []
    coins = []
    powerups = []
    hearts = []
    enemies = []

    improvements_manager = ImprovementsManager(bird)
    missions_manager = MissionsManager(bird)
    weather = Weather()
    save_manager = SaveManager(bird, missions_manager, improvements_manager)
    save_manager.load()

    speed = DIFFICULTIES[difficulty]["pipe_speed"]
    enemy_rate = DIFFICULTIES[difficulty]["enemy_rate"]
    pipe_timer = coin_timer = powerup_timer = heart_timer = enemy_timer = bg_timer = 0

    bg_index = 0

    game_over = False
    paused = False
    show_improvement_menu = False

    while True:
        screen.fill(BG_COLORS[bg_index])

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_manager.save()
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not game_over and not paused and not show_improvement_menu:
                    bird.jump()
                if event.key == pygame.K_p:
                    paused = not paused
                if event.key == pygame.K_m:
                    show_improvement_menu = not show_improvement_menu
                if show_improvement_menu:
                    if event.key == pygame.K_1:
                        improvements_manager.buy("magnet_duration")
                    if event.key == pygame.K_2:
                        improvements_manager.buy("shield_duration")
                    if event.key == pygame.K_3:
                        improvements_manager.buy("jump_power")
                if game_over and event.key == pygame.K_SPACE:
                    bird = Bird(bird_color)
                    pipes.clear(); coins.clear(); powerups.clear(); hearts.clear(); enemies.clear()
                    improvements_manager = ImprovementsManager(bird)
                    missions_manager = MissionsManager(bird)
                    weather = Weather()
                    save_manager = SaveManager(bird, missions_manager, improvements_manager)
                    save_manager.load()
                    game_over = False

        if not paused and not game_over and not show_improvement_menu:
            pipe_timer += 1
            coin_timer += 1
            powerup_timer += 1
            heart_timer += 1
            enemy_timer += 1
            bg_timer += 1

            if pipe_timer > 90:
                pipes.append(Pipe(WIDTH))
                pipe_timer = 0

            if coin_timer > 150:
                coins.append(Coin(WIDTH, random.randint(50, HEIGHT - 50)))
                coin_timer = 0

            if powerup_timer > 600:
                kind = random.choice(["shield", "magnet"])
                powerups.append(PowerUp(WIDTH, random.randint(50, HEIGHT - 50), kind))
                powerup_timer = 0

            if heart_timer > 900:
                hearts.append(Heart(WIDTH, random.randint(50, HEIGHT - 50)))
                heart_timer = 0

            if enemy_timer > enemy_rate:
                enemies.append(Enemy(WIDTH, random.randint(50, HEIGHT - 50)))
                enemy_timer = 0

            if bg_timer > 600:
                bg_timer = 0
                bg_index = (bg_index + 1) % len(BG_COLORS)

            weather.update()
            weather.apply_effect(bird)

            bird.update()

            # Падение вниз
            if bird.y > HEIGHT:
                if bird.immunity == 0 and not bird.shield:
                    bird.health -= 25
                    bird.immunity = 120
                    if bird.health <= 0:
                        bird.lives -= 1
                        bird.health = 100
                        bird.immunity = 120
                        if bird.lives <= 0:
                            game_over = True
                bird.y = HEIGHT - bird.height
                bird.vel = 0
                bird.rect.y = int(bird.y)

            # Пайпы
            for pipe in pipes[:]:
                pipe.update(speed)
                pipe.draw()
                if pipe.x + pipe.width < 0:
                    pipes.remove(pipe)
                if bird.rect.colliderect(pipe.rect_top) or bird.rect.colliderect(pipe.rect_bottom):
                    if not bird.shield and bird.immunity == 0:
                        bird.health -= 25
                        bird.immunity = 120
                        if bird.health <= 0:
                            bird.lives -= 1
                            bird.health = 100
                            bird.immunity = 120
                            if bird.lives <= 0:
                                game_over = True
                if not pipe.scored and pipe.x + pipe.width < bird.x:
                    bird.score += 1
                    pipe.scored = True
                    missions_manager.update()

            # Монеты
            for coin in coins[:]:
                coin.update(speed)
                coin.draw()
                if coin.rect.right < 0:
                    coins.remove(coin)
                if not coin.collected and bird.rect.colliderect(coin.rect):
                    coin.collected = True
                    bird.coins += 1
                    missions_manager.update()

            # PowerUps
            for pu in powerups[:]:
                pu.update(speed)
                pu.draw()
                if pu.rect.right < 0:
                    powerups.remove(pu)
                if bird.rect.colliderect(pu.rect):
                    if pu.kind == "shield":
                        bird.shield = True
                        bird.shield_duration = improvements_manager.improvements["shield_duration"]["level"] * 300
                    else:
                        bird.magnet_duration = improvements_manager.improvements["magnet_duration"]["level"] * 300
                    powerups.remove(pu)

            # Сердца
            for heart in hearts[:]:
                heart.update(speed)
                heart.draw()
                if heart.rect.right < 0:
                    hearts.remove(heart)
                if not heart.collected and bird.rect.colliderect(heart.rect):
                    heart.collected = True
                    bird.lives = min(bird.lives + 1, 5)
                    missions_manager.hearts_collected += 1
                    hearts.remove(heart)
                    missions_manager.update()

            # Враги
            for enemy in enemies[:]:
                enemy.update()
                enemy.draw()
                if enemy.rect.right < 0:
                    enemies.remove(enemy)
                if bird.rect.colliderect(enemy.rect):
                    if not bird.shield and bird.immunity == 0:
                        bird.health -= 25
                        bird.immunity = 120
                        enemies.remove(enemy)
                        if bird.health <= 0:
                            bird.lives -= 1
                            bird.health = 100
                            bird.immunity = 120
                            if bird.lives <= 0:
                                game_over = True

            # HUD
            draw_text(f"Очки: {bird.score}", 10, 10)
            draw_text(f"Монеты: {bird.coins}", 10, 40)
            draw_text(f"Жизни: {bird.lives}", 10, 70)
            draw_text(f"Здоровье: {bird.health}", 10, 100)
            draw_text(f"Погода: {weather.type}", 10, 130)
            draw_health_bar(120, 100, bird.health)
            draw_mission_progress(missions_manager)


            weather.draw()
            bird.draw()

        elif paused:
            draw_text("Пауза. Нажмите P для продолжения.", WIDTH // 2 - 150, HEIGHT // 2)
        elif show_improvement_menu:
            improvements_manager.draw_menu()
            draw_text("Нажмите P для паузы, M для выхода", 50, HEIGHT - 40)
        else:
            draw_text("Игра окончена!", WIDTH // 2 - 70, HEIGHT // 2 - 30, (255, 0, 0))
            draw_text("Нажмите SPACE для новой игры", WIDTH // 2 - 140, HEIGHT // 2 + 10, (255, 0, 0))

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
