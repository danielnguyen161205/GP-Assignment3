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

PARTICLE_SPAWN_PER_FLAP = 15
PARTICLE_LIFETIME_MS = 500

DIFFICULTY_RAMP_PER_SEC = 0.08
MAX_DIFFICULTY_MULTIPLIER = 2.2
MIN_GAP_SIZE = 125
MAX_GAP_SIZE = 250

# --- Assets ---
BG_IMAGE = "assets/sprites/background-day.png"
GROUND_IMAGE = "assets/sprites/base.png"
CLOUD_IMAGE = "assets/sprites/cloud_lonely.png"

# Player sprites – Bird
BIRD_IDLE_FRAME_PATHS = [
    "assets/bird/PNG/frame-3.png",
    "assets/bird/PNG/frame-4.png",
]
BIRD_ACTIVE_FRAME_PATHS = [
    "assets/bird/PNG/frame-1.png",
    "assets/bird/PNG/frame-2.png",
    "assets/bird/PNG/frame-3.png",
]
# Player sprites – Dragon
DRAGON_IDLE_FRAME_PATHS = [
    "assets/dragon/PNG/frame-3.png",
    "assets/dragon/PNG/frame-4.png",
]
DRAGON_ACTIVE_FRAME_PATHS = [
    "assets/dragon/PNG/frame-1.png",
    "assets/dragon/PNG/frame-2.png",
    "assets/dragon/PNG/frame-3.png",
]

CHARACTERS = {
    "bird":   {"idle": BIRD_IDLE_FRAME_PATHS,   "active": BIRD_ACTIVE_FRAME_PATHS,   "size": (52, 40)},
    "dragon": {"idle": DRAGON_IDLE_FRAME_PATHS, "active": DRAGON_ACTIVE_FRAME_PATHS, "size": (58, 44)},
}

DIFFICULTY_PRESETS = {
    "easy":   {"speed": 3.0, "pipe_move": False, "label": "EASY",   "color": (46, 204, 113)},
    "medium": {"speed": 4.0, "pipe_move": True,  "label": "MEDIUM", "color": (241, 196, 15)},
    "hard":   {"speed": 5.5, "pipe_move": True,  "label": "HARD",   "color": (231, 76, 60)},
}

# Obstacle & collectible
OBSTACLE_IMAGE = "assets/sprites/pipe-green.png"
COLLECTIBLE_FRAME_PATHS = [
    "assets/star-coin-rotate/star-coin-rotate-1.png",
    "assets/star-coin-rotate/star-coin-rotate-2.png",
    "assets/star-coin-rotate/star-coin-rotate-3.png",
    "assets/star-coin-rotate/star-coin-rotate-4.png",
    "assets/star-coin-rotate/star-coin-rotate-5.png",
    "assets/star-coin-rotate/star-coin-rotate-6.png",
]

# States
STATE_MENU = "MENU"
STATE_PLAYING = "PLAYING"
STATE_GAMEOVER = "GAMEOVER"
STATE_SETTINGS = "SETTINGS"
