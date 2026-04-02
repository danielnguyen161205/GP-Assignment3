import pygame
import random
import sys
import math

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GROUND_Y, GROUND_HEIGHT,
    COLLECTIBLE_SCORE, OBSTACLE_SPAWN_INTERVAL_MS,
    DYNAMIC_OBSTACLE_MIN_AMPLITUDE, DYNAMIC_OBSTACLE_MAX_AMPLITUDE,
    DYNAMIC_OBSTACLE_MIN_ANGULAR_SPEED, DYNAMIC_OBSTACLE_MAX_ANGULAR_SPEED,
    PARTICLE_SPAWN_PER_FLAP,
    DIFFICULTY_RAMP_PER_SEC, MAX_DIFFICULTY_MULTIPLIER,
    MIN_GAP_SIZE, MAX_GAP_SIZE,
    BG_IMAGE, GROUND_IMAGE, CHARACTERS, DIFFICULTY_PRESETS,
    STATE_MENU, STATE_PLAYING, STATE_GAMEOVER, STATE_SETTINGS,
)
from sprites import (
    draw_outlined_text, Button, BackgroundLayer,
    Player, Obstacle, Collectible, Particle, Cloud,
)


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

        # Overlay for menus (convert_alpha for fast blitting)
        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 120))
        self.overlay = self.overlay.convert_alpha()
        
        # Adjustable Settings
        self.selected_character = "bird"   # "bird" or "dragon"
        self.selected_difficulty = "medium" # "easy", "medium", "hard"
        self._apply_difficulty_preset()
        self.state = STATE_MENU
        self.reset_game()

        # Pre-load character previews for settings screen
        self._char_previews = {}
        for cname, cdata in CHARACTERS.items():
            try:
                img = pygame.image.load(cdata["idle"][0]).convert_alpha()
                img = pygame.transform.smoothscale(img, (78, 60))
            except pygame.error:
                img = pygame.Surface((78, 60), pygame.SRCALPHA)
                img.fill((200, 200, 200))
            self._char_previews[cname] = img

        # UI Buttons
        bw, bh = 220, 55
        cx = SCREEN_WIDTH // 2 - bw // 2
        self.start_btn = Button("START GAME", cx, 270, bw, bh, (34, 139, 34), (50, 180, 50))
        self.settings_btn = Button("SETTINGS", cx, 340, bw, bh, (70, 70, 90), (100, 100, 130))
        self.restart_btn = Button("RESTART", cx, 340, bw, bh, (180, 50, 50), (220, 80, 80))
        self.menu_btn = Button("MAIN MENU", cx, 410, bw, bh, (70, 70, 90), (100, 100, 130))
        self.back_btn = Button("BACK", cx + 50, 500, 120, 48, (70, 70, 90), (100, 100, 130))

        # Settings – character buttons
        char_bw, char_bh = 130, 44
        char_y = 210
        char_left = SCREEN_WIDTH // 2 - char_bw - 20
        self.char_bird_btn = Button("BIRD", char_left, char_y, char_bw, char_bh,
                                     (50, 120, 180), (70, 150, 220))
        self.char_dragon_btn = Button("DRAGON", char_left + char_bw + 40, char_y, char_bw, char_bh,
                                       (50, 120, 180), (70, 150, 220))

        # Settings – difficulty buttons
        diff_bw, diff_bh = 100, 44
        diff_y = 370
        diff_start_x = SCREEN_WIDTH // 2 - int(1.5 * diff_bw) - 20
        self.diff_easy_btn = Button("EASY", diff_start_x, diff_y, diff_bw, diff_bh,
                                     (46, 204, 113), (56, 224, 133))
        self.diff_medium_btn = Button("MEDIUM", diff_start_x + diff_bw + 20, diff_y, diff_bw, diff_bh,
                                       (241, 196, 15), (255, 216, 45))
        self.diff_hard_btn = Button("HARD", diff_start_x + 2 * (diff_bw + 20), diff_y, diff_bw, diff_bh,
                                     (231, 76, 60), (251, 96, 80))

    def _apply_difficulty_preset(self):
        preset = DIFFICULTY_PRESETS[self.selected_difficulty]
        self.base_speed = preset["speed"]
        self.pipe_move_enabled = preset["pipe_move"]

    def reset_game(self):
        self.score = 0
        self.current_speed = self.base_speed
        self.difficulty_time_sec = 0.0
        self.difficulty_multiplier = 1.0
        self.player = pygame.sprite.GroupSingle(Player(self.selected_character))
        self.obstacles = pygame.sprite.Group()
        self.spawn_timer_ms = 0
        self.collectibles = pygame.sprite.Group()
        self.particles = []
        # 3-layer parallax: sky (slowest), city (medium), ground (fastest)
        self.layers = self._build_parallax_layers()
        # Floating clouds on sky layer
        self.clouds = [
            Cloud(random.randint(0, SCREEN_WIDTH), random.randint(15, 80), scale=1.4),
            Cloud(random.randint(0, SCREEN_WIDTH), random.randint(40, 130), scale=2.0),
            Cloud(random.randint(0, SCREEN_WIDTH), random.randint(60, 170), scale=1.7),
            Cloud(random.randint(0, SCREEN_WIDTH), random.randint(20, 100), scale=1.2),
            Cloud(random.randint(0, SCREEN_WIDTH), random.randint(100, 200), scale=1.8),
        ]

    @staticmethod
    def _build_parallax_layers():
        # Load source image and split into sky / city regions
        try:
            raw = pygame.image.load(BG_IMAGE).convert()
            raw_w, raw_h = raw.get_size()
            # Sky: top ~55%
            sky_h = int(raw_h * 0.55)
            sky_region = raw.subsurface(pygame.Rect(0, 0, raw_w, sky_h))
            # City/buildings: middle ~25% (including clouds)
            city_start = int(raw_h * 0.42)
            city_h = int(raw_h * 0.30)
            city_region = raw.subsurface(pygame.Rect(0, city_start, raw_w, city_h))
        except pygame.error:
            sky_region = None
            city_region = None

        city_display_h = 280
        city_y = GROUND_Y - city_display_h

        if sky_region is not None:
            sky_scaled_w = max(1, int(sky_region.get_width() * (SCREEN_HEIGHT / sky_region.get_height())))
            sky_surf = pygame.transform.scale(sky_region, (sky_scaled_w, SCREEN_HEIGHT))
        else:
            sky_surf = None
        if city_region is not None:
            city_scaled_w = max(1, int(city_region.get_width() * (city_display_h / city_region.get_height())))
            city_surf = pygame.transform.scale(city_region, (city_scaled_w, city_display_h)).convert_alpha()
        else:
            city_surf = None

        sky_layer = BackgroundLayer(BG_IMAGE, 0.15, 0, SCREEN_HEIGHT, (78, 192, 202),
                                    surface=sky_surf)
        city_layer = BackgroundLayer(BG_IMAGE, 0.5, city_y, city_display_h, (95, 180, 120),
                                     surface=city_surf)
        ground_layer = BackgroundLayer(GROUND_IMAGE, 1.0, GROUND_Y, GROUND_HEIGHT, (222, 216, 149))
        return [sky_layer, city_layer, ground_layer]

    def _draw_bg(self):
        for layer in self.layers:
            layer.draw(self.screen)

    def _update_bg(self):
        for layer in self.layers:
            layer.update(self.current_speed)
        for c in self.clouds:
            c.update(self.current_speed)

    def _draw_clouds(self):
        for c in self.clouds:
            c.draw(self.screen)

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

        # Pipes start fixed, gradually gain oscillation as difficulty increases
        if not self.pipe_move_enabled or difficulty_ratio < 0.15:
            # No pipe movement (disabled or early game)
            amp = 0.0
            omega = 0.0
        else:
            # Scale oscillation from 0 to full range based on difficulty
            move_ratio = min(1.0, (difficulty_ratio - 0.15) / 0.55)
            amp = move_ratio * random.uniform(DYNAMIC_OBSTACLE_MIN_AMPLITUDE, DYNAMIC_OBSTACLE_MAX_AMPLITUDE)
            omega = move_ratio * random.uniform(DYNAMIC_OBSTACLE_MIN_ANGULAR_SPEED, DYNAMIC_OBSTACLE_MAX_ANGULAR_SPEED)
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
                    if self.start_btn.is_clicked(event):
                        self.reset_game()
                        self.state = STATE_PLAYING
                    if self.settings_btn.is_clicked(event): self.state = STATE_SETTINGS
                
                elif self.state == STATE_SETTINGS:
                    if self.char_bird_btn.is_clicked(event): self.selected_character = "bird"
                    if self.char_dragon_btn.is_clicked(event): self.selected_character = "dragon"
                    if self.diff_easy_btn.is_clicked(event):
                        self.selected_difficulty = "easy"; self._apply_difficulty_preset()
                    if self.diff_medium_btn.is_clicked(event):
                        self.selected_difficulty = "medium"; self._apply_difficulty_preset()
                    if self.diff_hard_btn.is_clicked(event):
                        self.selected_difficulty = "hard"; self._apply_difficulty_preset()
                    if self.back_btn.is_clicked(event): self.state = STATE_MENU
                
                elif self.state == STATE_PLAYING:
                    pass
                
                elif self.state == STATE_GAMEOVER:
                    if self.restart_btn.is_clicked(event):
                        self.reset_game()
                        self.state = STATE_PLAYING
                    if self.menu_btn.is_clicked(event):
                        self.reset_game()
                        self.state = STATE_MENU

            self.screen.fill((78, 192, 202))

            if self.state == STATE_MENU:
                self._update_bg()
                self._draw_bg()
                self._draw_clouds()
                self.screen.blit(self.overlay, (0, 0))
                draw_outlined_text(self.screen, "INFINITE FLYER", SCREEN_WIDTH // 2, 150,
                                   self.title_font, (255, 255, 100), (0, 0, 0), 3)
                self.start_btn.draw(self.screen)
                self.settings_btn.draw(self.screen)

            elif self.state == STATE_SETTINGS:
                self._update_bg()
                self._draw_bg()
                self._draw_clouds()
                self.screen.blit(self.overlay, (0, 0))
                draw_outlined_text(self.screen, "SETTINGS", SCREEN_WIDTH // 2, 80,
                                   self.title_font, (255, 255, 255), (0, 0, 0), 3)

                # ---- Character section ----
                draw_outlined_text(self.screen, "CHARACTER", SCREEN_WIDTH // 2, 170,
                                   self.info_font, (255, 220, 100), (0, 0, 0), 2)
                self.char_bird_btn.draw(self.screen)
                self.char_dragon_btn.draw(self.screen)

                # Selection highlight box
                sel_btn = self.char_bird_btn if self.selected_character == "bird" else self.char_dragon_btn
                pygame.draw.rect(self.screen, (255, 255, 100), sel_btn.rect.inflate(6, 6), width=3, border_radius=14)

                # Character previews below buttons
                for cname, btn in [("bird", self.char_bird_btn), ("dragon", self.char_dragon_btn)]:
                    preview = self._char_previews[cname]
                    px = btn.rect.centerx - preview.get_width() // 2
                    py = btn.rect.bottom + 8
                    self.screen.blit(preview, (px, py))

                # ---- Difficulty section ----
                draw_outlined_text(self.screen, "DIFFICULTY", SCREEN_WIDTH // 2, 335,
                                   self.info_font, (255, 220, 100), (0, 0, 0), 2)
                self.diff_easy_btn.draw(self.screen)
                self.diff_medium_btn.draw(self.screen)
                self.diff_hard_btn.draw(self.screen)

                # Selection highlight
                diff_btn_map = {"easy": self.diff_easy_btn, "medium": self.diff_medium_btn, "hard": self.diff_hard_btn}
                sel_diff = diff_btn_map[self.selected_difficulty]
                pygame.draw.rect(self.screen, (255, 255, 100), sel_diff.rect.inflate(6, 6), width=3, border_radius=14)

                # Description of selected difficulty
                preset = DIFFICULTY_PRESETS[self.selected_difficulty]
                pipe_desc = "Pipes move" if preset["pipe_move"] else "Pipes static"
                desc_text = f"Speed: {preset['speed']}  |  {pipe_desc}"
                draw_outlined_text(self.screen, desc_text, SCREEN_WIDTH // 2, 435,
                                   self.info_font, (220, 220, 220), (0, 0, 0), 2)

                self.back_btn.draw(self.screen)

            elif self.state == STATE_PLAYING:
                # Mechanics
                self._update_difficulty(dt)
                self._update_bg()
                self._draw_bg()
                self._draw_clouds()

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
                self._draw_clouds()
                self.obstacles.draw(self.screen)
                self.player.draw(self.screen)
                self.screen.blit(self.overlay, (0, 0))
                draw_outlined_text(self.screen, "GAME OVER", SCREEN_WIDTH // 2, 200,
                                   self.title_font, (255, 80, 80), (0, 0, 0), 3)
                draw_outlined_text(self.screen, f"FINAL SCORE: {self.score}", SCREEN_WIDTH // 2, 280,
                                   self.info_font, (255, 255, 255), (0, 0, 0), 2)
                self.restart_btn.draw(self.screen)
                self.menu_btn.draw(self.screen)

            pygame.display.flip()

if __name__ == "__main__":
    Game().run()