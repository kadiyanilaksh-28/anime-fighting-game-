
import pygame
import os
import math
from array import array

# ============== AUDIO + PYGAME ==============
try:
    pygame.mixer.pre_init(22050, -16, 1, 512)
except Exception:
    pass

pygame.init()

SOUND_ENABLED = False
SOUNDS = {}

try:
    if not pygame.mixer.get_init():
        pygame.mixer.init(22050, -16, 1, 512)
    SOUND_ENABLED = True
except Exception:
    SOUND_ENABLED = False


def make_sound(freq, duration, volume=0.3, slide=0):
    """Create sound effects without external audio files."""
    if not SOUND_ENABLED:
        return None

    try:
        sample_rate = 22050
        count = int(sample_rate * duration)
        samples = array("h")

        for i in range(count):
            t = i / sample_rate
            progress = i / max(1, count)
            current_freq = freq + slide * progress

            envelope = (1.0 - progress) ** 2
            wave = math.sin(
                2 * math.pi * current_freq * t
            )

            value = int(
                32767 * volume * envelope * wave
            )
            samples.append(max(-32767, min(32767, value)))

        return pygame.mixer.Sound(buffer=samples)

    except Exception:
        return None


def make_sequence(notes):
    """Join short notes into one sound."""
    if not SOUND_ENABLED:
        return None

    try:
        sample_rate = 22050
        samples = array("h")

        for freq, duration, volume in notes:
            count = int(sample_rate * duration)

            for i in range(count):
                t = i / sample_rate
                progress = i / max(1, count)
                envelope = (1.0 - progress) ** 2

                value = int(
                    32767 * volume * envelope *
                    math.sin(2 * math.pi * freq * t)
                )
                samples.append(
                    max(-32767, min(32767, value))
                )

        return pygame.mixer.Sound(buffer=samples)

    except Exception:
        return None


if SOUND_ENABLED:
    SOUNDS = {
        "punch": make_sound(190, 0.12, 0.45, -100),
        "jump": make_sound(360, 0.16, 0.25, 300),
        "rasengan": make_sound(180, 0.35, 0.35, 850),
        "hit": make_sound(120, 0.18, 0.45, -50),
        "damage": make_sound(95, 0.25, 0.45, -40),
        "defeat": make_sound(250, 0.30, 0.35, -180),
        "menu": make_sound(520, 0.08, 0.20, 100),
        "win": make_sequence([
            (523, 0.15, 0.3),
            (659, 0.15, 0.3),
            (784, 0.25, 0.35),
            (1047, 0.40, 0.35)
        ]),
        "lose": make_sequence([
            (440, 0.20, 0.3),
            (350, 0.25, 0.3),
            (260, 0.40, 0.3)
        ])
    }


def play_sound(name):
    if not SOUND_ENABLED:
        return

    sound = SOUNDS.get(name)

    if sound is not None:
        try:
            sound.play()
        except Exception:
            pass


# ============== FULL SCREEN ==============
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
W, H = screen.get_size()
pygame.display.set_caption("Anime Fighting Game")
clock = pygame.time.Clock()

FONT = pygame.font.Font(None, max(22, H // 20))
BIG = pygame.font.Font(None, max(40, H // 10))
SMALL = pygame.font.Font(None, max(18, H // 30))

WHITE = (245, 245, 255)
BLACK = (15, 18, 32)
BLUE = (45, 135, 255)
RED = (245, 65, 75)
GREEN = (55, 225, 115)
YELLOW = (255, 205, 55)
PURPLE = (155, 85, 255)
CYAN = (40, 230, 255)

GROUND = int(H * .78)
PW = max(28, int(W * .043))
PH = max(48, int(H * .17))

SAVE_DIR = os.path.dirname(os.path.abspath(__file__))
LEVEL_FILE = os.path.join(SAVE_DIR, "anime_progress.txt")
SCORE_FILE = os.path.join(SAVE_DIR, "anime_highscore.txt")


def read_number(path, default=0):
    try:
        with open(path, "r") as f:
            return max(default, int(f.read().strip()))
    except Exception:
        return default


def save_number(path, number):
    try:
        with open(path, "w") as f:
            f.write(str(number))
    except Exception:
        pass


unlocked_level = max(1, read_number(LEVEL_FILE, 1))
high_score = read_number(SCORE_FILE, 0)

level = 1
score = 0
state = "menu"

player = {}
enemies = []
rasengans = []
effects = []
overlay_rects = []


# ============== BUTTONS ==============
buttons = {
    "left": pygame.Rect(
        int(W*.025), int(H*.80),
        int(W*.075), int(H*.14)
    ),
    "right": pygame.Rect(
        int(W*.11), int(H*.80),
        int(W*.075), int(H*.14)
    ),
    "face_left": pygame.Rect(
        int(W*.22), int(H*.80),
        int(W*.09), int(H*.14)
    ),
    "face_right": pygame.Rect(
        int(W*.32), int(H*.80),
        int(W*.09), int(H*.14)
    ),
    "punch": pygame.Rect(
        int(W*.43), int(H*.80),
        int(W*.105), int(H*.14)
    ),
    "jump": pygame.Rect(
        int(W*.55), int(H*.80),
        int(W*.09), int(H*.14)
    ),
    "rasengan": pygame.Rect(
        int(W*.66), int(H*.79),
        int(W*.20), int(H*.15)
    ),
    "menu": pygame.Rect(
        int(W*.88), int(H*.025),
        int(W*.10), int(H*.07)
    )
}


# ============== DIFFICULTY ==============
def enemy_count():
    return min(level, 10)


def move_speed():
    return min(W * (.006 + (level-1)*.0003), W*.012)


def enemy_speed():
    return min(W * (.0016 + (level-1)*.0002), W*.005)


def enemy_max_hp():
    return min(100 + (level-1)*10, 500)


def save_score():
    global high_score

    if score > high_score:
        high_score = score
        save_number(SCORE_FILE, high_score)


# ============== LEVEL SETUP ==============
def reset_level():
    global player, enemies, rasengans, effects, state

    player = {
        "x": W*.18,
        "y": 0.0,
        "vy": 0.0,
        "hp": 100,
        "face": 1,
        "move": 0,
        "ground": True,
        "attack_cd": 0,
        "punch_cd": 0
    }

    enemies = []
    rasengans = []
    effects = []

    count = enemy_count()
    hp = enemy_max_hp()

    for i in range(count):
        enemies.append({
            "x": W*(.55 + .04*i),
            "hp": hp,
            "maxhp": hp,
            "attack_cd": 30 + i*8,
            "face": -1,
            "alive": True
        })

    state = "playing"


def start_game():
    global level
    level = min(level, unlocked_level)
    reset_level()


# ============== DRAW HELPERS ==============
def text_center(txt, font, color, rect):
    img = font.render(txt, True, color)
    screen.blit(img, img.get_rect(center=rect.center))


def draw_button(rect, label, color):
    pygame.draw.rect(
        screen, color, rect, border_radius=12
    )
    pygame.draw.rect(
        screen, WHITE, rect, 2, border_radius=12
    )
    text_center(label, SMALL, WHITE, rect)


def draw_health(x, y, width, hp, maximum, color):
    bar_h = max(10, int(H*.025))

    pygame.draw.rect(
        screen, (45,45,60),
        (x, y, width, bar_h), border_radius=5
    )

    ratio = max(0, min(1, hp/maximum))

    pygame.draw.rect(
        screen, color,
        (x, y, int(width*ratio), bar_h),
        border_radius=5
    )


def draw_background():
    screen.fill((115,190,245))

    pygame.draw.circle(
        screen, WHITE,
        (int(W*.15), int(H*.13)), int(H*.04)
    )
    pygame.draw.circle(
        screen, WHITE,
        (int(W*.18), int(H*.12)), int(H*.05)
    )
    pygame.draw.circle(
        screen, WHITE,
        (int(W*.21), int(H*.14)), int(H*.035)
    )

    pygame.draw.polygon(screen, (90,175,140), [
        (0, GROUND),
        (W*.20, H*.40),
        (W*.42, GROUND)
    ])

    pygame.draw.polygon(screen, (70,155,125), [
        (W*.35, GROUND),
        (W*.61, H*.43),
        (W*.85, GROUND)
    ])

    pygame.draw.rect(
        screen, (65,175,100),
        (0, GROUND, W, H-GROUND)
    )

    pygame.draw.line(
        screen, (40,125,70),
        (0, GROUND), (W, GROUND), 4
    )


def draw_ninja(x, y, color, face, enemy_mode=False):
    x, y = int(x), int(y)

    leg_color = (
        (30,35,85) if not enemy_mode else (100,20,35)
    )

    pygame.draw.ellipse(
        screen, (35,55,55),
        (x-5, GROUND-7, PW+12, 12)
    )

    pygame.draw.line(
        screen, leg_color,
        (x+PW*.35, y+PH*.68),
        (x+PW*.25, y+PH), 7
    )

    pygame.draw.line(
        screen, leg_color,
        (x+PW*.68, y+PH*.68),
        (x+PW*.80, y+PH), 7
    )

    pygame.draw.rect(
        screen, color,
        (x+PW*.15, y+PH*.32, PW*.72, PH*.43),
        border_radius=7
    )

    hx = x+PW*.50
    hy = y+PH*.19

    pygame.draw.circle(
        screen, (255,205,160),
        (int(hx), int(hy)), int(PW*.39)
    )

    hair = BLACK if not enemy_mode else (45,20,35)

    pygame.draw.polygon(screen, hair, [
        (int(hx-PW*.38), int(hy)),
        (int(hx-PW*.35), int(hy-PH*.17)),
        (int(hx-PW*.08), int(hy-PH*.09)),
        (int(hx+PW*.12), int(hy-PH*.19)),
        (int(hx+PW*.40), int(hy-PH*.04)),
        (int(hx+PW*.37), int(hy+PH*.05))
    ])

    pygame.draw.line(
        screen, CYAN,
        (int(hx-PW*.32), int(hy)),
        (int(hx+PW*.32), int(hy)), 4
    )

    eye_x = hx+face*PW*.17

    pygame.draw.circle(
        screen, BLACK,
        (int(eye_x), int(hy+PH*.02)),
        max(2, int(PW*.045))
    )


# ============== RASENGAN ==============
def fire_rasengan():
    if state != "playing" or player["attack_cd"] > 0:
        return

    player["attack_cd"] = 12
    direction = player["face"]

    rasengans.append({
        "x": player["x"]+PW*.5+direction*PW*.6,
        "y": GROUND-PH+player["y"]+PH*.48,
        "vx": direction*W*.020,
        "life": 100
    })

    play_sound("rasengan")


# ============== PUNCH ATTACK ==============
def punch_enemy():
    global score

    if state != "playing" or player["punch_cd"] > 0:
        return

    player["punch_cd"] = 18
    play_sound("punch")

    candidates = []

    for e in enemies:
        if not e["alive"]:
            continue

        distance = e["x"] - player["x"]

        if (
            abs(distance) <= PW * 2.8
            and distance * player["face"] >= -PW * .3
        ):
            candidates.append((abs(distance), e))

    if candidates:
        _, e = min(candidates, key=lambda item: item[0])
        e["hp"] -= 20

        effects.append([
            e["x"] + PW*.5,
            GROUND - PH*.5,
            int(H*.05)
        ])

        play_sound("hit")

        if e["hp"] <= 0:
            e["hp"] = 0
            e["alive"] = False
            score += 100
            save_score()
            play_sound("defeat")


def next_level():
    global level, unlocked_level

    level += 1
    unlocked_level = max(unlocked_level, level)

    save_number(LEVEL_FILE, unlocked_level)
    reset_level()


# ============== GAME DISPLAY ==============
def draw_game():
    draw_background()

    screen.blit(
        FONT.render(f"LEVEL {level}", True, BLACK),
        (15, 10)
    )

    screen.blit(
        FONT.render(f"SCORE: {score}", True, BLACK),
        (15, int(H*.14))
    )

    screen.blit(
        FONT.render(f"HIGH SCORE: {high_score}", True, BLACK),
        (15, int(H*.19))
    )

    draw_health(
        int(W*.02), int(H*.08), int(W*.26),
        player["hp"], 100, GREEN
    )

    screen.blit(
        SMALL.render("PLAYER", True, BLACK),
        (int(W*.02), int(H*.105))
    )

    alive = [e for e in enemies if e["alive"]]

    screen.blit(
        SMALL.render(
            f"ENEMIES LEFT: {len(alive)}", True, BLACK
        ),
        (int(W*.72), int(H*.14))
    )

    draw_ninja(
        player["x"], GROUND-PH+player["y"],
        BLUE, player["face"]
    )

    for e in alive:
        draw_ninja(
            e["x"], GROUND-PH,
            RED, e["face"], True
        )

        draw_health(
            int(e["x"]-10), GROUND-PH-20,
            PW+20, e["hp"], e["maxhp"], RED
        )

    for r in rasengans:
        cx, cy = int(r["x"]), int(r["y"])
        radius = max(10, int(H*.035))

        pygame.draw.circle(
            screen, (30,110,255), (cx,cy), radius
        )
        pygame.draw.circle(
            screen, CYAN, (cx,cy), int(radius*.68)
        )
        pygame.draw.circle(
            screen, WHITE, (cx,cy), int(radius*.3)
        )

    for e in effects:
        pygame.draw.circle(
            screen, YELLOW,
            (int(e[0]), int(e[1])),
            max(2, int(e[2])), 2
        )

    draw_button(buttons["left"], "MOVE L", (45,75,150))
    draw_button(buttons["right"], "MOVE R", (45,75,150))
    draw_button(buttons["face_left"], "FACE L", (100,65,150))
    draw_button(buttons["face_right"], "FACE R", (100,65,150))
    draw_button(buttons["punch"], "PUNCH", (200,75,55))
    draw_button(buttons["jump"], "JUMP", (100,75,180))
    draw_button(buttons["rasengan"], "RASENGAN", (40,90,230))
    draw_button(buttons["menu"], "MENU", (55,55,80))


# ============== OVERLAYS ==============
def draw_overlay(title, options):
    overlay = pygame.Surface((W,H), pygame.SRCALPHA)
    overlay.fill((5,10,25,205))
    screen.blit(overlay, (0,0))

    img = BIG.render(title, True, YELLOW)
    screen.blit(
        img, img.get_rect(center=(W//2, int(H*.24)))
    )

    rects = []
    bh = int(H*.095)
    gap = int(H*.025)

    total = len(options)*bh+(len(options)-1)*gap
    start = (H-total)//2+int(H*.08)

    for i, (label, color) in enumerate(options):
        rect = pygame.Rect(
            int(W*.25),
            start+i*(bh+gap),
            int(W*.50), bh
        )

        draw_button(rect, label, color)
        rects.append((rect, label))

    return rects


# ============== MENU ACTIONS ==============
def handle_overlay_click(pos):
    global state

    for rect, label in overlay_rects:
        if rect.collidepoint(pos):
            play_sound("menu")

            if label == "PLAY":
                start_game()

            elif label == "RESUME":
                state = "playing"

            elif label == "RESTART CURRENT LEVEL":
                reset_level()

            elif label == "MAIN MENU":
                state = "menu"

            elif label == "NEXT LEVEL":
                next_level()

            elif label == "QUIT":
                return False

            return True

    return True


def handle_game_press(pos):
    global state

    if buttons["menu"].collidepoint(pos):
        player["move"] = 0
        play_sound("menu")
        state = "paused"

    elif buttons["left"].collidepoint(pos):
        player["move"] = -1

    elif buttons["right"].collidepoint(pos):
        player["move"] = 1

    elif buttons["face_left"].collidepoint(pos):
        player["face"] = -1

    elif buttons["face_right"].collidepoint(pos):
        player["face"] = 1

    elif buttons["punch"].collidepoint(pos):
        punch_enemy()

    elif buttons["jump"].collidepoint(pos):
        if player["ground"]:
            player["vy"] = -H*.045
            player["ground"] = False
            play_sound("jump")

    elif buttons["rasengan"].collidepoint(pos):
        fire_rasengan()


# ============== MAIN LOOP ==============
reset_level()
state = "menu"
running = True

while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if state == "playing":
                    state = "paused"
                    player["move"] = 0
                elif state == "paused":
                    state = "playing"
                else:
                    running = False

            if state == "playing":
                if event.key == pygame.K_LEFT:
                    player["move"] = -1

                elif event.key == pygame.K_RIGHT:
                    player["move"] = 1

                elif event.key == pygame.K_a:
                    player["face"] = -1

                elif event.key == pygame.K_d:
                    player["face"] = 1

                elif event.key in (pygame.K_UP, pygame.K_SPACE):
                    if player["ground"]:
                        player["vy"] = -H*.045
                        player["ground"] = False
                        play_sound("jump")

                elif event.key == pygame.K_f:
                    punch_enemy()

                elif event.key == pygame.K_r:
                    fire_rasengan()

        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                player["move"] = 0

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if state in ("menu", "paused", "won", "lost"):
                if not handle_overlay_click(event.pos):
                    running = False
            else:
                handle_game_press(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP:
            player["move"] = 0

        elif event.type == pygame.FINGERDOWN:
            pos = (int(event.x*W), int(event.y*H))

            if state in ("menu", "paused", "won", "lost"):
                if not handle_overlay_click(pos):
                    running = False
            else:
                handle_game_press(pos)

        elif event.type == pygame.FINGERUP:
            player["move"] = 0

    # ============== UPDATE GAME ==============
    if state == "playing":
        player["x"] += player["move"] * move_speed()
        player["x"] = max(0, min(W-PW, player["x"]))

        # Jump physics
        player["vy"] += H*.0038
        player["y"] += player["vy"]

        if player["y"] >= 0:
            player["y"] = 0
            player["vy"] = 0
            player["ground"] = True

        # Keep player on-screen
        if player["y"] < -H*.20:
            player["y"] = -H*.20
            player["vy"] = 0

        if player["attack_cd"] > 0:
            player["attack_cd"] -= 1

        if player["punch_cd"] > 0:
            player["punch_cd"] -= 1

        # ============== ENEMY AI ==============
        for e in enemies:
            if not e["alive"]:
                continue

            if e["attack_cd"] > 0:
                e["attack_cd"] -= 1

            distance = player["x"] - e["x"]

            if abs(distance) > PW*1.5:
                e["x"] += (
                    1 if distance > 0 else -1
                ) * enemy_speed()

                e["face"] = 1 if distance > 0 else -1

            elif e["attack_cd"] == 0:
                old_hp = player["hp"]
                player["hp"] = max(0, player["hp"]-5)
                e["attack_cd"] = 45

                if player["hp"] < old_hp:
                    play_sound("damage")

            e["x"] = max(0, min(W-PW, e["x"]))

        if player["hp"] <= 0:
            save_score()
            state = "lost"
            play_sound("lose")

        # ============== RASENGAN COLLISION ==============
        for r in rasengans[:]:
            r["x"] += r["vx"]
            r["life"] -= 1

            radius = max(10, int(H*.035))

            rr = pygame.Rect(
                int(r["x"])-radius,
                int(r["y"])-radius,
                radius*2,
                radius*2
            )

            for e in enemies:
                if not e["alive"]:
                    continue

                er = pygame.Rect(
                    int(e["x"]-radius*.35),
                    int(GROUND-PH-radius*.15),
                    int(PW+radius*.7),
                    int(PH+radius*.3)
                )

                if rr.colliderect(er):
                    e["hp"] -= 25

                    effects.append([
                        r["x"], r["y"], int(H*.05)
                    ])

                    play_sound("hit")

                    if r in rasengans:
                        rasengans.remove(r)

                    if e["hp"] <= 0:
                        e["hp"] = 0
                        e["alive"] = False
                        score += 100
                        save_score()
                        play_sound("defeat")

                    break

            if r in rasengans and (
                r["life"] <= 0
                or r["x"] < -50
                or r["x"] > W+50
            ):
                rasengans.remove(r)

        # ============== EFFECTS ==============
        for e in effects[:]:
            e[2] -= 1

            if e[2] <= 0:
                effects.remove(e)

        # ============== WIN CONDITION ==============
        if all(not e["alive"] for e in enemies):
            save_score()
            state = "won"
            play_sound("win")

    # ============== RENDER ==============
    if state == "menu":
        draw_background()

        overlay_rects = draw_overlay("ANIME FIGHTING", [
            ("PLAY", (40,125,70)),
            ("RESTART CURRENT LEVEL", (65,80,180)),
            ("QUIT", (130,50,60))
        ])

    elif state == "playing":
        draw_game()

    elif state == "paused":
        draw_game()

        overlay_rects = draw_overlay("PAUSED", [
            ("RESUME", (40,125,70)),
            ("RESTART CURRENT LEVEL", (65,80,180)),
            ("MAIN MENU", (75,80,130))
        ])

    elif state == "won":
        draw_game()

        overlay_rects = draw_overlay("YOU WIN!", [
            ("NEXT LEVEL", (40,125,70)),
            ("RESTART CURRENT LEVEL", (65,80,180)),
            ("MAIN MENU", (75,80,130))
        ])

    elif state == "lost":
        draw_game()

        overlay_rects = draw_overlay("GAME OVER", [
            ("RESTART CURRENT LEVEL", (65,80,180)),
            ("MAIN MENU", (75,80,130))
        ])

    pygame.display.flip()

save_score()
pygame.quit()
