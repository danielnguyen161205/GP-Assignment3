import pygame
import random
import sys
import math

# --- Configuration & Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GROUND_HEIGHT = 56
GROUND_Y = SCREEN_HEIGHT - GROUND_HEIGHT

# Player physics (time-based, unit: pixels/second^2)
GRAVITY_ACCEL = 1700.0
FLAP_IMPULSE = -470.0
MAX_FALL_SPEED = 750.0
MAX_RISE_SPEED = -520.0
FLAP_STATE_DURATION_MS = 120

# Animation timing (milliseconds)
IDLE_ANIM_INTERVAL_MS = 180
ACTIVE_ANIM_INTERVAL_MS = 90
COIN_ANIM_INTERVAL_MS = 90
COLLECTIBLE_SCORE = 5

# Obstacle/collectible spawn tuning
OBSTACLE_SPAWN_INTERVAL_MS = 1600
OBSTACLE_WIDTH = 70
PIPE_CAP_HEIGHT = 26

# Extension tuning (Requirement 5)
DYNAMIC_OBSTACLE_MIN_AMPLITUDE = 25
DYNAMIC_OBSTACLE_MAX_AMPLITUDE = 95
DYNAMIC_OBSTACLE_MIN_ANGULAR_SPEED = 1.2
DYNAMIC_OBSTACLE_MAX_ANGULAR_SPEED = 2.4

PARTICLE_SPAWN_PER_FLAP = 8
PARTICLE_LIFETIME_MS = 320

DIFFICULTY_RAMP_PER_SEC = 0.08
MAX_DIFFICULTY_MULTIPLIER = 2.2
MIN_GAP_SIZE = 125
MAX_GAP_SIZE = 250

# --- Assets ---
BG_IMAGE = "assets/sprites/background-day.png"
GROUND_IMAGE = "assets/sprites/base.png"

# Player sprite
PLAYER_IDLE_FRAME_PATHS = [
    "assets/bird/PNG/frame-3.png",
    "assets/bird/PNG/frame-4.png",
]
PLAYER_ACTIVE_FRAME_PATHS = [
    "assets/bird/PNG/frame-1.png",
    "assets/bird/PNG/frame-2.png",
    "assets/bird/PNG/frame-3.png",
]

# Obstacle & collectible
OBSTACLE_IMAGE = "assets/sprites/pipe-green.png"
COLLECTIBLE_FRAME_PATHS = [
    "assets/star-coin-rotate/star-coin-rotate-1.png",
    "assets/star-coin-rotate/star-coin-rotate-2.png",
    "assets/star-coin-rotate/star-coin-rotate-3.png",
    "assets/star-coin-rotate/star-coin-rotate-4.png",
    "assets/star-coin-rotate/star-coin-rotate-5.png",
    "assets/star-coin-rotate/star-coin-rotate-6.png"
]

# States
STATE_MENU = "MENU"
STATE_PLAYING = "PLAYING"
STATE_GAMEOVER = "GAMEOVER"
STATE_SETTINGS = "SETTINGS"

_text_cache = {}

def draw_outlined_text(screen, text, x, y, font, color=(255, 255, 255), outline_color=(0, 0, 0), outline_width=2, center=True):
    key = (text, id(font), color, outline_color, outline_width)
    if key not in _text_cache:
        text_surf = font.render(text, True, color)
        tw, th = text_surf.get_size()
        pad = outline_width
        combined = pygame.Surface((tw + pad * 2, th + pad * 2), pygame.SRCALPHA)
        outline_surf = font.render(text, True, outline_color)
        # 8 directions only (much faster than full grid)
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
            combined.blit(outline_surf, (pad + dx * outline_width, pad + dy * outline_width))
        combined.blit(text_surf, (pad, pad))
        _text_cache[key] = combined
    cached = _text_cache[key]
    if center:
        rect = cached.get_rect(center=(x, y))
    else:
        rect = cached.get_rect(topleft=(x - outline_width, y - outline_width))
    screen.blit(cached, rect)


class Button:
    _shared_font = None

    def __init__(self, text, x, y, width, height, color, hover_color):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.hover_color = hover_color
        if Button._shared_font is None:
            Button._shared_font = pygame.font.SysFont("Arial", 28, bold=True)
        self.font = Button._shared_font
        # Pre-render highlight surface
        self._highlight = pygame.Surface((self.rect.width, self.rect.height // 2), pygame.SRCALPHA)
        self._highlight.fill((255, 255, 255, 40))

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        hovered = self.rect.collidepoint(mouse_pos)
        current_color = self.hover_color if hovered else self.color

        shadow_rect = self.rect.move(3, 3)
        pygame.draw.rect(screen, (0, 0, 0, 80), shadow_rect, border_radius=12)
        pygame.draw.rect(screen, current_color, self.rect, border_radius=12)
        screen.blit(self._highlight, self.rect.topleft)
        border_color = (255, 255, 255, 120) if hovered else (0, 0, 0, 60)
        pygame.draw.rect(screen, border_color, self.rect, width=2, border_radius=12)

        draw_outlined_text(screen, self.text, self.rect.centerx, self.rect.centery,
                           self.font, (255, 255, 255), (0, 0, 0), 1)

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

class BackgroundLayer:
    def __init__(self, image_path, speed_multiplier, y_pos, height, fallback_color):
        self.speed_multiplier = speed_multiplier
        self.y_pos = y_pos
        self.height = height

        try:
            raw_image = pygame.image.load(image_path).convert()
            raw_w, raw_h = raw_image.get_size()
            scaled_w = max(1, int(raw_w * (height / raw_h)))
            self.image = pygame.transform.scale(raw_image, (scaled_w, height))
        except pygame.error as e:
            print(f"Unable to load image: {image_path} - {e}")
            self.image = pygame.Surface((SCREEN_WIDTH, height))
            self.image.fill(fallback_color)

        self.width = self.image.get_width()

        # Pre-build a wide strip that covers 2x screen for seamless tiling
        if self.width < SCREEN_WIDTH * 2:
            repeats = (SCREEN_WIDTH * 2 // self.width) + 1
            wide_surf = pygame.Surface((self.width * repeats, height))
            for i in range(repeats):
                wide_surf.blit(self.image, (i * self.width, 0))
            self.image = wide_surf
            self.width = self.image.get_width()

        self.offset = 0.0

    def update(self, global_speed):
        move_speed = global_speed * self.speed_multiplier
        self.offset = (self.offset + move_speed) % self.width

    def draw(self, screen):
        start_x = -int(self.offset)
        x = start_x
        while x < SCREEN_WIDTH:
            screen.blit(self.image, (x, self.y_pos))
            x += self.width

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.idle_frames = self._load_frames(PLAYER_IDLE_FRAME_PATHS, [(240, 110, 110), (220, 110, 110)])
        self.active_frames = self._load_frames(PLAYER_ACTIVE_FRAME_PATHS, [(255, 80, 80), (255, 100, 80), (255, 120, 80)])

        self.state = "idle"
        self.current_frames = self.idle_frames
        self.frame_index = 0
        self.image = self.current_frames[self.frame_index]
        self.rect = self.image.get_rect(center=(150, 300))
        self.y = float(self.rect.y)

        # Vertical speed (pixels/second).
        self.velocity_y = 0.0
        self.anim_timer_ms = 0
        self.flap_state_timer_ms = 0

    def _load_frames(self, image_paths, fallback_colors):
        frames = []
        for i, path in enumerate(image_paths):
            try:
                image = pygame.image.load(path).convert_alpha()
                image = pygame.transform.smoothscale(image, (52, 40))
                frames.append(image)
            except pygame.error:
                fallback = pygame.Surface((52, 40), pygame.SRCALPHA)
                fallback.fill(fallback_colors[i % len(fallback_colors)])
                frames.append(fallback)
        return frames

    def _set_state(self, new_state):
        if new_state == self.state:
            return

        self.state = new_state
        self.current_frames = self.active_frames if self.state == "active" else self.idle_frames
        self.frame_index = 0
        self.image = self.current_frames[self.frame_index]

    def _update_animation(self, dt_ms):
        self.anim_timer_ms += dt_ms
        interval = ACTIVE_ANIM_INTERVAL_MS if self.state == "active" else IDLE_ANIM_INTERVAL_MS
        while self.anim_timer_ms >= interval:
            self.anim_timer_ms -= interval
            self.frame_index = (self.frame_index + 1) % len(self.current_frames)
            self.image = self.current_frames[self.frame_index]

    def update(self, dt_ms, flap_requested):
        dt_sec = dt_ms / 1000.0

        # Tap to Flap: each input gives a single upward impulse.
        if flap_requested:
            self.velocity_y = FLAP_IMPULSE
            self.flap_state_timer_ms = FLAP_STATE_DURATION_MS

        self.velocity_y += GRAVITY_ACCEL * dt_sec
        self.velocity_y = max(MAX_RISE_SPEED, min(MAX_FALL_SPEED, self.velocity_y))

        self.y += self.velocity_y * dt_sec
        self.rect.y = int(self.y)

        self.flap_state_timer_ms = max(0, self.flap_state_timer_ms - dt_ms)
        self._set_state("active" if self.flap_state_timer_ms > 0 else "idle")
        self._update_animation(dt_ms)

class Obstacle(pygame.sprite.Sprite):
    _cap_cache = None
    _body_cache = None

    def __init__(self, x, is_top, gap_y, gap_size, dynamic_amp=0.0, dynamic_omega=0.0, dynamic_phase=0.0):
        super().__init__()
        self.is_top = is_top
        self.gap_y = float(gap_y)
        self.gap_size = gap_size

        self.dynamic_amp = float(dynamic_amp)
        self.dynamic_omega = float(dynamic_omega)
        self.dynamic_phase = float(dynamic_phase)
        self.time_sec = 0.0

        cap, body_slice = self._get_pipe_parts()

        if is_top:
            segment_height = max(PIPE_CAP_HEIGHT + 4, gap_y - gap_size // 2)
        else:
            segment_height = max(PIPE_CAP_HEIGHT + 4, GROUND_Y - (gap_y + gap_size // 2))

        self.image = self._build_pipe(cap, body_slice, segment_height, is_top)

        if is_top:
            self.rect = self.image.get_rect(bottomleft=(x, gap_y - gap_size // 2))
        else:
            self.rect = self.image.get_rect(topleft=(x, gap_y + gap_size // 2))

        self.float_x = float(self.rect.x)
        self.base_y = float(self.rect.y)

    @classmethod
    def _get_pipe_parts(cls):
        if cls._cap_cache is not None:
            return cls._cap_cache, cls._body_cache

        try:
            raw = pygame.image.load(OBSTACLE_IMAGE).convert_alpha()
            raw_w, raw_h = raw.get_size()
            # Cap is the wider top part of the pipe image
            cap_h = max(1, int(raw_h * 0.16))
            cap_region = raw.subsurface(pygame.Rect(0, 0, raw_w, cap_h))
            # Body is a thin slice from the middle
            body_y = cap_h + 2
            body_region = raw.subsurface(pygame.Rect(0, body_y, raw_w, min(4, raw_h - body_y)))
            cls._cap_cache = pygame.transform.smoothscale(cap_region, (OBSTACLE_WIDTH, PIPE_CAP_HEIGHT))
            cls._body_cache = pygame.transform.smoothscale(body_region, (OBSTACLE_WIDTH - 8, 4))
        except pygame.error:
            cls._cap_cache = pygame.Surface((OBSTACLE_WIDTH, PIPE_CAP_HEIGHT), pygame.SRCALPHA)
            cls._cap_cache.fill((80, 200, 80))
            pygame.draw.rect(cls._cap_cache, (60, 160, 60), cls._cap_cache.get_rect(), width=2)
            cls._body_cache = pygame.Surface((OBSTACLE_WIDTH - 8, 4), pygame.SRCALPHA)
            cls._body_cache.fill((90, 190, 90))
        return cls._cap_cache, cls._body_cache

    @staticmethod
    def _build_pipe(cap, body_slice, total_height, is_top):
        surf = pygame.Surface((OBSTACLE_WIDTH, total_height), pygame.SRCALPHA)
        body_w = body_slice.get_width()
        body_x = (OBSTACLE_WIDTH - body_w) // 2

        if is_top:
            # Body fills from top, cap at bottom (near gap)
            body_h = total_height - PIPE_CAP_HEIGHT
            for y in range(0, body_h, body_slice.get_height()):
                surf.blit(body_slice, (body_x, y))
            flipped_cap = pygame.transform.flip(cap, False, True)
            surf.blit(flipped_cap, (0, total_height - PIPE_CAP_HEIGHT))
        else:
            # Cap at top (near gap), body fills below
            surf.blit(cap, (0, 0))
            body_h = total_height - PIPE_CAP_HEIGHT
            for y in range(PIPE_CAP_HEIGHT, total_height, body_slice.get_height()):
                surf.blit(body_slice, (body_x, y))
        return surf

    def update(self, speed, dt_ms):
        dt_sec = dt_ms / 1000.0
        self.float_x -= speed
        self.rect.x = int(self.float_x)

        self.time_sec += dt_sec
        if self.dynamic_amp > 0.0:
            y_offset = self.dynamic_amp * math.sin(self.dynamic_omega * self.time_sec + self.dynamic_phase)
            self.rect.y = int(self.base_y + y_offset)

        if self.rect.right < 0:
            self.kill()  # Despawn to free memory.


class Collectible(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.frames = self._load_frames(COLLECTIBLE_FRAME_PATHS)
        self.index = 0
        self.image = self.frames[self.index]
        self.rect = self.image.get_rect(center=(x, y))
        self.float_x = float(self.rect.x)
        self.anim_timer_ms = 0

    def _load_frames(self, image_paths):
        frames = []
        for i, path in enumerate(image_paths):
            try:
                frame = pygame.image.load(path).convert_alpha()
                frame = pygame.transform.smoothscale(frame, (30, 30))
            except pygame.error:
                # Fallback spinning coin-like silhouette if image is not provided yet.
                frame = pygame.Surface((30, 30), pygame.SRCALPHA)
                width = max(6, 30 - (i * 5))
                pygame.draw.ellipse(frame, (255, 215, 0), (15 - width // 2, 0, width, 30))
            frames.append(frame)
        return frames

    def update(self, speed, dt_ms):
        self.float_x -= speed
        self.rect.x = int(self.float_x)

        self.anim_timer_ms += dt_ms
        while self.anim_timer_ms >= COIN_ANIM_INTERVAL_MS:
            self.anim_timer_ms -= COIN_ANIM_INTERVAL_MS
            self.index = (self.index + 1) % len(self.frames)
            self.image = self.frames[self.index]

        if self.rect.right < 0:
            self.kill()


class Particle:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-220, -120)
        self.vy = random.uniform(-120, 120)
        self.life_ms = PARTICLE_LIFETIME_MS
        self.max_life_ms = PARTICLE_LIFETIME_MS
        self.size = random.randint(2, 5)
        self.color = random.choice([
            (245, 245, 245),
            (225, 225, 225),
            (255, 220, 180),
        ])

    def update(self, dt_ms):
        dt_sec = dt_ms / 1000.0
        self.life_ms -= dt_ms
        self.x += self.vx * dt_sec
        self.y += self.vy * dt_sec
        self.vy += 420.0 * dt_sec

    def draw(self, screen):
        if self.life_ms <= 0:
            return
        alpha = max(0.0, self.life_ms / self.max_life_ms)
        radius = max(1, int(self.size * alpha))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), radius)

    @property
    def alive(self):
        return self.life_ms > 0


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Infinite Flyer")
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("Arial", 60, bold=True)
        self.score_font = pygame.font.SysFont("Arial", 42, bold=True)
        self.info_font = pygame.font.SysFont("Arial", 30, bold=True)
        self._last_score_text = None

        # Overlay for menus
        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 120))
        
        # Adjustable Settings
        self.base_speed = 4.0 
        self.state = STATE_MENU
        self.reset_game()

        # UI Buttons
        bw, bh = 220, 55
        cx = SCREEN_WIDTH // 2 - bw // 2
        self.start_btn = Button("START GAME", cx, 270, bw, bh, (34, 139, 34), (50, 180, 50))
        self.settings_btn = Button("SETTINGS", cx, 340, bw, bh, (70, 70, 90), (100, 100, 130))
        self.restart_btn = Button("RESTART", cx, 360, bw, bh, (180, 50, 50), (220, 80, 80))
        self.speed_up_btn = Button("SPEED +", cx + bw // 2 + 10, 300, 110, 48, (40, 80, 180), (60, 110, 220))
        self.speed_down_btn = Button("SPEED -", cx - 120, 300, 110, 48, (40, 80, 180), (60, 110, 220))
        self.back_btn = Button("BACK", cx + 50, 420, 120, 48, (70, 70, 90), (100, 100, 130))

    def reset_game(self):
        self.score = 0
        self.current_speed = self.base_speed
        self.difficulty_time_sec = 0.0
        self.difficulty_multiplier = 1.0
        self.player = pygame.sprite.GroupSingle(Player())
        self.obstacles = pygame.sprite.Group()
        self.spawn_timer_ms = 0
        self.collectibles = pygame.sprite.Group()
        self.particles = []
        # Background: full-screen sky, then ground strip
        self.bg_layer = BackgroundLayer(BG_IMAGE, 0.3, 0, SCREEN_HEIGHT, (78, 192, 202))
        self.ground_layer = BackgroundLayer(GROUND_IMAGE, 1.0, GROUND_Y, GROUND_HEIGHT, (222, 216, 149))

    def _draw_bg(self):
        self.bg_layer.draw(self.screen)
        self.ground_layer.draw(self.screen)

    def _update_bg(self):
        self.bg_layer.update(self.current_speed)
        self.ground_layer.update(self.current_speed)

    def _check_game_over_collision(self):
        player_sprite = self.player.sprite
        if player_sprite is None:
            return False

        hit_obstacle = pygame.sprite.spritecollideany(player_sprite, self.obstacles) is not None
        hit_ground = player_sprite.rect.bottom >= GROUND_Y
        hit_ceiling = player_sprite.rect.top <= 0
        return hit_obstacle or hit_ground or hit_ceiling

    def _collect_collectibles(self):
        player_sprite = self.player.sprite
        if player_sprite is None:
            return

        collected = pygame.sprite.spritecollide(player_sprite, self.collectibles, True)
        if collected:
            self.score += COLLECTIBLE_SCORE * len(collected)

    def _spawn_flap_particles(self):
        player_sprite = self.player.sprite
        if player_sprite is None:
            return

        origin_x = player_sprite.rect.left + 4
        origin_y = player_sprite.rect.centery
        for _ in range(PARTICLE_SPAWN_PER_FLAP):
            self.particles.append(Particle(origin_x, origin_y))

    def _update_particles(self, dt_ms):
        for p in self.particles:
            p.update(dt_ms)
        self.particles = [p for p in self.particles if p.alive]

    def _draw_particles(self):
        for p in self.particles:
            p.draw(self.screen)

    def _update_difficulty(self, dt_ms):
        self.difficulty_time_sec += dt_ms / 1000.0
        scaled = 1.0 + self.difficulty_time_sec * DIFFICULTY_RAMP_PER_SEC
        self.difficulty_multiplier = min(MAX_DIFFICULTY_MULTIPLIER, scaled)
        self.current_speed = self.base_speed * self.difficulty_multiplier

    def _spawn_obstacle_and_collectible(self):
        # Difficulty affects gap size and obstacle movement intensity.
        difficulty_ratio = (self.difficulty_multiplier - 1.0) / (MAX_DIFFICULTY_MULTIPLIER - 1.0)
        difficulty_ratio = max(0.0, min(1.0, difficulty_ratio))

        dynamic_gap_max = int(MAX_GAP_SIZE - 70 * difficulty_ratio)
        gap_size = random.randint(MIN_GAP_SIZE, max(MIN_GAP_SIZE + 5, dynamic_gap_max))
        gap_y = random.randint(120, GROUND_Y - 120)

        amp = random.uniform(DYNAMIC_OBSTACLE_MIN_AMPLITUDE, DYNAMIC_OBSTACLE_MAX_AMPLITUDE)
        omega = random.uniform(DYNAMIC_OBSTACLE_MIN_ANGULAR_SPEED, DYNAMIC_OBSTACLE_MAX_ANGULAR_SPEED)
        phase = random.uniform(0.0, 2.0 * math.pi)

        spawn_x = SCREEN_WIDTH + 50
        top = Obstacle(spawn_x, True, gap_y, gap_size, amp, omega, phase)
        bot = Obstacle(spawn_x, False, gap_y, gap_size, amp, omega, phase)
        self.obstacles.add(top)
        self.obstacles.add(bot)

        collectible_y = random.randint(gap_y - gap_size // 3, gap_y + gap_size // 3)
        self.collectibles.add(Collectible(SCREEN_WIDTH + 150, collectible_y))

    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                
                if self.state == STATE_MENU:
                    if self.start_btn.is_clicked(event): self.state = STATE_PLAYING
                    if self.settings_btn.is_clicked(event): self.state = STATE_SETTINGS
                
                elif self.state == STATE_SETTINGS:
                    if self.speed_up_btn.is_clicked(event): self.base_speed += 1
                    if self.speed_down_btn.is_clicked(event): self.base_speed = max(2, self.base_speed - 1)
                    if self.back_btn.is_clicked(event): self.state = STATE_MENU
                
                elif self.state == STATE_PLAYING:
                    pass
                
                elif self.state == STATE_GAMEOVER:
                    if self.restart_btn.is_clicked(event):
                        self.reset_game()
                        self.state = STATE_PLAYING

            self.screen.fill((78, 192, 202))

            if self.state == STATE_MENU:
                self._update_bg()
                self._draw_bg()
                self.screen.blit(self.overlay, (0, 0))
                draw_outlined_text(self.screen, "INFINITE FLYER", SCREEN_WIDTH // 2, 150,
                                   self.title_font, (255, 255, 100), (0, 0, 0), 3)
                self.start_btn.draw(self.screen)
                self.settings_btn.draw(self.screen)

            elif self.state == STATE_SETTINGS:
                self._update_bg()
                self._draw_bg()
                self.screen.blit(self.overlay, (0, 0))
                draw_outlined_text(self.screen, "SETTINGS", SCREEN_WIDTH // 2, 120,
                                   self.title_font, (255, 255, 255), (0, 0, 0), 3)
                draw_outlined_text(self.screen, f"Starting Speed: {self.base_speed}", SCREEN_WIDTH // 2, 240,
                                   self.info_font, (255, 255, 255), (0, 0, 0), 2)
                self.speed_up_btn.draw(self.screen)
                self.speed_down_btn.draw(self.screen)
                self.back_btn.draw(self.screen)

            elif self.state == STATE_PLAYING:
                # Mechanics
                self._update_difficulty(dt)
                self._update_bg()
                self._draw_bg()

                flap_requested = False
                for event in events:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                        flap_requested = True
                        self._spawn_flap_particles()
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        flap_requested = True
                        self._spawn_flap_particles()
                
                # Time-based spawning so behavior is stable across frame rates.
                self.spawn_timer_ms += dt
                spawn_interval = max(650, int(OBSTACLE_SPAWN_INTERVAL_MS / self.difficulty_multiplier))
                while self.spawn_timer_ms >= spawn_interval:
                    self._spawn_obstacle_and_collectible()
                    self.spawn_timer_ms -= spawn_interval

                # --- Update & Draw Collectibles ---
                self.collectibles.update(self.current_speed, dt)
                self.collectibles.draw(self.screen)

                # --- Particle system ---
                self._update_particles(dt)
                self._draw_particles()

                # --- Collision Detection for Collectibles ---
                self._collect_collectibles()

                self.player.update(dt, flap_requested)
                self.obstacles.update(self.current_speed, dt)

                # Collision [cite: 53, 54]
                if self._check_game_over_collision():
                    self.state = STATE_GAMEOVER

                self.obstacles.draw(self.screen)
                self.player.draw(self.screen)
                score_text = f"SCORE: {self.score}"
                draw_outlined_text(self.screen, score_text, SCREEN_WIDTH // 2, 50,
                                   self.score_font, (255, 255, 255), (0, 0, 0), 2)

            elif self.state == STATE_GAMEOVER:
                self._draw_bg()
                self.obstacles.draw(self.screen)
                self.player.draw(self.screen)
                self.screen.blit(self.overlay, (0, 0))
                draw_outlined_text(self.screen, "GAME OVER", SCREEN_WIDTH // 2, 200,
                                   self.title_font, (255, 80, 80), (0, 0, 0), 3)
                draw_outlined_text(self.screen, f"FINAL SCORE: {self.score}", SCREEN_WIDTH // 2, 280,
                                   self.info_font, (255, 255, 255), (0, 0, 0), 2)
                self.restart_btn.draw(self.screen)

            pygame.display.flip()

if __name__ == "__main__":
    Game().run()