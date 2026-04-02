import pygame
import random
import math

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GROUND_Y, GROUND_HEIGHT,
    GRAVITY_ACCEL, FLAP_IMPULSE, MAX_FALL_SPEED, MAX_RISE_SPEED,
    FLAP_STATE_DURATION_MS, IDLE_ANIM_INTERVAL_MS, ACTIVE_ANIM_INTERVAL_MS,
    COIN_ANIM_INTERVAL_MS, PARTICLE_LIFETIME_MS, PARTICLE_SPAWN_PER_FLAP,
    OBSTACLE_WIDTH, PIPE_CAP_HEIGHT, OBSTACLE_IMAGE,
    BG_IMAGE, GROUND_IMAGE, CLOUD_IMAGE,
    CHARACTERS, COLLECTIBLE_FRAME_PATHS,
)

# ---------------------------------------------------------------------------
# Cached outlined-text rendering
# ---------------------------------------------------------------------------
_text_cache = {}


def draw_outlined_text(screen, text, x, y, font, color=(255, 255, 255),
                       outline_color=(0, 0, 0), outline_width=2, center=True):
    key = (text, id(font), color, outline_color, outline_width)
    if key not in _text_cache:
        text_surf = font.render(text, True, color)
        tw, th = text_surf.get_size()
        pad = outline_width
        combined = pygame.Surface((tw + pad * 2, th + pad * 2), pygame.SRCALPHA)
        outline_surf = font.render(text, True, outline_color)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                       (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            combined.blit(outline_surf,
                          (pad + dx * outline_width, pad + dy * outline_width))
        combined.blit(text_surf, (pad, pad))
        _text_cache[key] = combined
    cached = _text_cache[key]
    if center:
        rect = cached.get_rect(center=(x, y))
    else:
        rect = cached.get_rect(topleft=(x - outline_width, y - outline_width))
    screen.blit(cached, rect)


# ---------------------------------------------------------------------------
# UI Button
# ---------------------------------------------------------------------------
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
        self._highlight = pygame.Surface(
            (self.rect.width, self.rect.height // 2), pygame.SRCALPHA)
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
        pygame.draw.rect(screen, border_color, self.rect, width=2,
                         border_radius=12)

        draw_outlined_text(screen, self.text, self.rect.centerx,
                           self.rect.centery, self.font,
                           (255, 255, 255), (0, 0, 0), 1)

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False


# ---------------------------------------------------------------------------
# Background layer (parallax)
# ---------------------------------------------------------------------------
class BackgroundLayer:
    def __init__(self, image_path, speed_multiplier, y_pos, height,
                 fallback_color, surface=None):
        self.speed_multiplier = speed_multiplier
        self.y_pos = y_pos
        self.height = height

        if surface is not None:
            self.image = surface
        else:
            try:
                raw_image = pygame.image.load(image_path).convert()
                raw_w, raw_h = raw_image.get_size()
                scaled_w = max(1, int(raw_w * (height / raw_h)))
                self.image = pygame.transform.scale(raw_image,
                                                    (scaled_w, height))
            except pygame.error as e:
                print(f"Unable to load image: {image_path} - {e}")
                self.image = pygame.Surface((SCREEN_WIDTH, height))
                self.image.fill(fallback_color)

        self.width = self.image.get_width()

        if self.width < SCREEN_WIDTH * 2:
            repeats = (SCREEN_WIDTH * 2 // self.width) + 1
            has_alpha = self.image.get_flags() & pygame.SRCALPHA
            if has_alpha:
                wide_surf = pygame.Surface((self.width * repeats, height),
                                           pygame.SRCALPHA)
            else:
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


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player(pygame.sprite.Sprite):
    def __init__(self, character="bird"):
        super().__init__()
        char_data = CHARACTERS.get(character, CHARACTERS["bird"])
        self._sprite_size = char_data["size"]
        self.idle_frames = self._load_frames(
            char_data["idle"], [(240, 110, 110), (220, 110, 110)])
        self.active_frames = self._load_frames(
            char_data["active"],
            [(255, 80, 80), (255, 100, 80), (255, 120, 80)])

        self.state = "idle"
        self.current_frames = self.idle_frames
        self.frame_index = 0
        self.image = self.current_frames[self.frame_index]
        self.rect = self.image.get_rect(center=(150, 300))
        self.y = float(self.rect.y)

        self.velocity_y = 0.0
        self.anim_timer_ms = 0
        self.flap_state_timer_ms = 0

    def _load_frames(self, image_paths, fallback_colors):
        frames = []
        for i, path in enumerate(image_paths):
            try:
                image = pygame.image.load(path).convert_alpha()
                image = pygame.transform.smoothscale(image, self._sprite_size)
                frames.append(image)
            except pygame.error:
                fallback = pygame.Surface(self._sprite_size, pygame.SRCALPHA)
                fallback.fill(fallback_colors[i % len(fallback_colors)])
                frames.append(fallback)
        return frames

    def _set_state(self, new_state):
        if new_state == self.state:
            return
        self.state = new_state
        self.current_frames = (self.active_frames if self.state == "active"
                               else self.idle_frames)
        self.frame_index = 0
        self.image = self.current_frames[self.frame_index]

    def _update_animation(self, dt_ms):
        self.anim_timer_ms += dt_ms
        interval = (ACTIVE_ANIM_INTERVAL_MS if self.state == "active"
                    else IDLE_ANIM_INTERVAL_MS)
        while self.anim_timer_ms >= interval:
            self.anim_timer_ms -= interval
            self.frame_index = ((self.frame_index + 1)
                                % len(self.current_frames))
            self.image = self.current_frames[self.frame_index]

    def update(self, dt_ms, flap_requested):
        dt_sec = dt_ms / 1000.0

        if flap_requested:
            self.velocity_y = FLAP_IMPULSE
            self.flap_state_timer_ms = FLAP_STATE_DURATION_MS

        self.velocity_y += GRAVITY_ACCEL * dt_sec
        self.velocity_y = max(MAX_RISE_SPEED,
                              min(MAX_FALL_SPEED, self.velocity_y))

        self.y += self.velocity_y * dt_sec
        self.rect.y = int(self.y)

        self.flap_state_timer_ms = max(0, self.flap_state_timer_ms - dt_ms)
        self._set_state(
            "active" if self.flap_state_timer_ms > 0 else "idle")
        self._update_animation(dt_ms)


# ---------------------------------------------------------------------------
# Obstacle (pipe pair)
# ---------------------------------------------------------------------------
class Obstacle(pygame.sprite.Sprite):
    _cap_cache = None
    _body_cache = None

    def __init__(self, x, is_top, gap_y, gap_size,
                 dynamic_amp=0.0, dynamic_omega=0.0, dynamic_phase=0.0):
        super().__init__()
        self.is_top = is_top
        self.gap_y = float(gap_y)
        self.gap_size = gap_size

        self.dynamic_amp = float(dynamic_amp)
        self.dynamic_omega = float(dynamic_omega)
        self.dynamic_phase = float(dynamic_phase)
        self.time_sec = 0.0

        cap, body_slice = self._get_pipe_parts()

        extra = int(self.dynamic_amp) + 150

        if is_top:
            segment_height = max(PIPE_CAP_HEIGHT + 4,
                                 gap_y - gap_size // 2 + extra)
        else:
            segment_height = max(PIPE_CAP_HEIGHT + 4,
                                 GROUND_Y - (gap_y + gap_size // 2) + extra)

        self.image = self._build_pipe(cap, body_slice, segment_height, is_top)

        if is_top:
            self.rect = self.image.get_rect(
                bottomleft=(x, gap_y - gap_size // 2))
        else:
            self.rect = self.image.get_rect(
                topleft=(x, gap_y + gap_size // 2))

        self.float_x = float(self.rect.x)
        self.base_y = float(self.rect.y)

    @classmethod
    def _get_pipe_parts(cls):
        if cls._cap_cache is not None:
            return cls._cap_cache, cls._body_cache

        try:
            raw = pygame.image.load(OBSTACLE_IMAGE).convert_alpha()
            raw_w, raw_h = raw.get_size()
            cap_h = max(1, int(raw_h * 0.16))
            cap_region = raw.subsurface(pygame.Rect(0, 0, raw_w, cap_h))
            body_y = cap_h + 2
            body_region = raw.subsurface(
                pygame.Rect(0, body_y, raw_w, min(4, raw_h - body_y)))
            cls._cap_cache = pygame.transform.smoothscale(
                cap_region, (OBSTACLE_WIDTH, PIPE_CAP_HEIGHT))
            cls._body_cache = pygame.transform.smoothscale(
                body_region, (OBSTACLE_WIDTH, 4))
        except pygame.error:
            cls._cap_cache = pygame.Surface(
                (OBSTACLE_WIDTH, PIPE_CAP_HEIGHT), pygame.SRCALPHA)
            cls._cap_cache.fill((80, 200, 80))
            pygame.draw.rect(cls._cap_cache, (60, 160, 60),
                             cls._cap_cache.get_rect(), width=2)
            cls._body_cache = pygame.Surface(
                (OBSTACLE_WIDTH, 4), pygame.SRCALPHA)
            cls._body_cache.fill((90, 190, 90))
        return cls._cap_cache, cls._body_cache

    @staticmethod
    def _build_pipe(cap, body_slice, total_height, is_top):
        surf = pygame.Surface((OBSTACLE_WIDTH, total_height), pygame.SRCALPHA)

        if is_top:
            body_h = total_height - PIPE_CAP_HEIGHT
            if body_h > 0:
                body_col = pygame.transform.scale(
                    body_slice, (OBSTACLE_WIDTH, body_h))
                surf.blit(body_col, (0, 0))
            flipped_cap = pygame.transform.flip(cap, False, True)
            surf.blit(flipped_cap, (0, total_height - PIPE_CAP_HEIGHT))
        else:
            surf.blit(cap, (0, 0))
            body_h = total_height - PIPE_CAP_HEIGHT
            if body_h > 0:
                body_col = pygame.transform.scale(
                    body_slice, (OBSTACLE_WIDTH, body_h))
                surf.blit(body_col, (0, PIPE_CAP_HEIGHT))
        return surf.convert_alpha()

    def update(self, speed, dt_ms):
        dt_sec = dt_ms / 1000.0
        self.float_x -= speed
        self.rect.x = int(self.float_x)

        self.time_sec += dt_sec
        if self.dynamic_amp > 0.0:
            y_offset = self.dynamic_amp * math.sin(
                self.dynamic_omega * self.time_sec + self.dynamic_phase)
            self.rect.y = int(self.base_y + y_offset)

        if self.rect.right < 0:
            self.kill()


# ---------------------------------------------------------------------------
# Collectible (rotating coin)
# ---------------------------------------------------------------------------
class Collectible(pygame.sprite.Sprite):
    _shared_frames = None

    def __init__(self, x, y):
        super().__init__()
        if Collectible._shared_frames is None:
            Collectible._shared_frames = Collectible._load_frames_once(
                COLLECTIBLE_FRAME_PATHS)
        self.frames = Collectible._shared_frames
        self.index = 0
        self.image = self.frames[self.index]
        self.rect = self.image.get_rect(center=(x, y))
        self.float_x = float(self.rect.x)
        self.anim_timer_ms = 0

    @staticmethod
    def _load_frames_once(image_paths):
        frames = []
        for i, path in enumerate(image_paths):
            try:
                frame = pygame.image.load(path).convert_alpha()
                frame = pygame.transform.smoothscale(frame, (30, 30))
            except pygame.error:
                frame = pygame.Surface((30, 30), pygame.SRCALPHA)
                width = max(6, 30 - (i * 5))
                pygame.draw.ellipse(
                    frame, (255, 215, 0),
                    (15 - width // 2, 0, width, 30))
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


# ---------------------------------------------------------------------------
# Particle (flap effect)
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-280, -80)
        self.vy = random.uniform(-180, 180)
        self.life_ms = PARTICLE_LIFETIME_MS
        self.max_life_ms = PARTICLE_LIFETIME_MS
        self.size = random.randint(4, 10)
        self.color = random.choice([
            (255, 255, 255),
            (200, 230, 255),
            (255, 230, 150),
            (255, 200, 100),
            (180, 220, 255),
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
        pygame.draw.circle(screen, self.color,
                           (int(self.x), int(self.y)), radius)

    @property
    def alive(self):
        return self.life_ms > 0


# ---------------------------------------------------------------------------
# Cloud (decorative)
# ---------------------------------------------------------------------------
class Cloud:
    _image_cache = None

    def __init__(self, x, y, scale=1.0):
        if Cloud._image_cache is None:
            try:
                Cloud._image_cache = pygame.image.load(
                    CLOUD_IMAGE).convert_alpha()
            except pygame.error:
                Cloud._image_cache = pygame.Surface(
                    (100, 40), pygame.SRCALPHA)
                pygame.draw.ellipse(Cloud._image_cache,
                                    (255, 255, 255, 180), (0, 0, 100, 40))
        w = int(Cloud._image_cache.get_width() * scale)
        h = int(Cloud._image_cache.get_height() * scale)
        self.image = pygame.transform.smoothscale(
            Cloud._image_cache, (w, h))
        self.x = float(x)
        self.y = float(y)
        self.width = w

    def update(self, speed):
        self.x -= speed * 0.15
        if self.x + self.width < 0:
            self.x = SCREEN_WIDTH + random.randint(20, 200)
            self.y = random.randint(20, 200)

    def draw(self, screen):
        screen.blit(self.image, (int(self.x), int(self.y)))
