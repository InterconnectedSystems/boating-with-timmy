# =====================================================================
# "BOATING WITH TIMMY" - 16-BIT RETRO EDITION
# Android-adapted: touch virtual buttons + scaled rendering
# Original game logic unchanged.
# =====================================================================

import pygame
import random
import sys
import time
import math
import array
import os

# ── Android detection ──────────────────────────────────────────────
IS_ANDROID = ('ANDROID_ARGUMENT' in os.environ or
              hasattr(sys, 'getandroidapilevel'))

# ====================== INITIALIZATION ======================
pygame.init()
pygame.font.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# Logical resolution (game runs at this size internally)
SCREEN_WIDTH  = 640
SCREEN_HEIGHT = 480

# Physical display
if IS_ANDROID:
    display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
else:
    display = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
DISPLAY_W, DISPLAY_H = display.get_size()

# All drawing goes to this surface, then scaled to display
screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

pygame.display.set_caption("BOATING WITH TIMMY - Don't Trust The Captain!")
clock = pygame.time.Clock()

# Use default pygame font so it works on Android without system fonts
FONT_SMALL = pygame.font.Font(None, 18)
FONT_LARGE = pygame.font.Font(None, 28)
FONT_HUGE  = pygame.font.Font(None, 44)

# ── Scale touch coordinates → logical ─────────────────────────────
def to_logical(px, py):
    return px * SCREEN_WIDTH / DISPLAY_W, py * SCREEN_HEIGHT / DISPLAY_H

# ── Virtual button layout (logical coords) ────────────────────────
VBTN = {
    'left':   pygame.Rect( 10, 405,  70, 60),
    'up':     pygame.Rect( 90, 385,  70, 60),
    'right':  pygame.Rect(170, 405,  70, 60),
    'bail':   pygame.Rect(350, 395,  85, 70),   # SPACE
    'repair': pygame.Rect(445, 395,  85, 70),   # R
    'yell':   pygame.Rect(540, 395,  90, 70),   # M
    'start':  pygame.Rect(195, 385, 250, 60),   # ENTER on title
}
VBTN_LABELS = {
    'left': '◄', 'up': '▲', 'right': '►',
    'bail': 'BAIL', 'repair': 'FIX', 'yell': 'YELL', 'start': 'TOUCH TO START',
}

# 16-BIT COLOR PALETTE
COLOR_SKY        = (0, 120, 255)
COLOR_WATER      = (0, 80,  180)
COLOR_WATER_DARK = (0, 60,  140)
COLOR_BOAT       = (139, 69, 19)
COLOR_SAIL       = (255, 255, 100)
COLOR_MAST       = (200, 200, 200)
COLOR_TIMMY      = (255, 100, 100)
COLOR_HUD        = (255, 255, 255)
COLOR_HEALTH_GOOD= (0,   255, 0)
COLOR_HEALTH_BAD = (255,   0, 0)
COLOR_DEBUG      = (255, 255, 0)
COLOR_TITLE      = (255, 215, 0)

FPS             = 60
TARGET_DISTANCE = 5000
BOAT_SPEED_MAX  = 4.0
WAVE_AMPLITUDE  = 8

# ====================== PROCEDURAL SOUND ======================
def create_sound(freq, duration, volume=0.5):
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    amplitude   = int(32767 * volume)
    samples     = array.array('h', [0] * num_samples)
    for i in range(num_samples):
        t = float(i) / sample_rate
        samples[i] = int(amplitude * math.sin(2 * math.pi * freq * t))
    return pygame.mixer.Sound(buffer=samples.tobytes())

print("[DEBUG SOUND] Generating procedural sound effects...")
splash_sound     = create_sound(620, 0.25, 0.7)
wave_crash_sound = create_sound(180, 0.90, 0.8)
repair_sound     = create_sound(1100, 0.35, 0.6)
mast_rip_sound   = create_sound(80,  0.70, 0.8)
motor_fall_sound = create_sound(250, 0.60, 0.7)
timmy_laugh_sound= create_sound(820, 0.45, 0.5)
hazard_sound     = create_sound(320, 0.40, 0.65)

music_notes = [
    (262,0.25),(294,0.25),(330,0.25),(349,0.25),
    (392,0.50),(392,0.25),(440,0.25),(523,0.50),
    (392,0.25),(330,0.25),(294,0.25),(262,0.50),
]
music_channel = pygame.mixer.Channel(1)

# ====================== GAME CLASSES ======================
class Boat:
    def __init__(self):
        self.x = SCREEN_WIDTH  // 2
        self.y = SCREEN_HEIGHT // 2 + 50
        self.angle       = 0.0
        self.speed       = 0.0
        self.health      = 100.0
        self.water_level = 0.0
        self.fuel        = 100.0
        self.mast_intact = True
        self.motor_intact= True
        self.hole_count  = 0
        self._dbg_t      = time.time()

    def update(self, dt, wind, wave):
        self.angle += wind * 0.3 * dt * 30 + wave * 0.8
        self.angle  = max(-45, min(45, self.angle))
        spd = self.speed
        if not self.mast_intact:  spd *= 0.4
        if not self.motor_intact: spd *= 0.6
        vec = pygame.math.Vector2(1, 0).rotate(self.angle)
        self.x += spd * vec.x * dt * 60
        self.y += spd * vec.y * dt * 60
        if self.hole_count > 0:
            self.water_level += self.hole_count * 0.8 * dt
        if time.time() - self._dbg_t > 0.5:
            print(f"[DEBUG BOAT] x={self.x:.1f} y={self.y:.1f} angle={self.angle:.1f} "
                  f"health={self.health:.1f} water={self.water_level:.1f} fuel={self.fuel:.1f} "
                  f"mast={self.mast_intact} motor={self.motor_intact} holes={self.hole_count}")
            self._dbg_t = time.time()

    def draw(self, surface):
        hull = pygame.Surface((80, 30), pygame.SRCALPHA)
        pygame.draw.polygon(hull, COLOR_BOAT, [(0,15),(80,15),(70,30),(10,30)])
        pygame.draw.line(hull, (0,0,0), (10,15),(70,15), 3)
        if self.mast_intact:
            pygame.draw.line(hull, COLOR_MAST, (40,15),(40,-25), 6)
            sail = [(40,-25),(70,-5),(40,15)]
            pygame.draw.polygon(hull, COLOR_SAIL, sail)
            pygame.draw.polygon(hull, (0,0,0), sail, 2)
        if self.motor_intact:
            pygame.draw.rect(hull, (50,50,50),(65,18,15,8))
            pygame.draw.circle(hull,(200,200,200),(75,22),4)
        for i in range(self.hole_count):
            pygame.draw.circle(hull,(0,0,0),(20+i*15,22),3)
        if self.water_level > 0:
            wh = int(30*(self.water_level/100))
            pygame.draw.rect(hull,(0,80,180),(5,30-wh,70,wh))
        rotated = pygame.transform.rotate(hull, -self.angle)
        surface.blit(rotated,(self.x-40, self.y-15))

    def take_damage(self, amount, reason):
        self.health -= amount
        print(f"[DEBUG HAZARD] {reason} -{amount}hp  hp={self.health:.1f}")


class CaptainTimmy:
    def __init__(self):
        self.sabotage_cooldown = 0
        self.dialogue = [
            "Heh heh... whoops, I 'accidentally' loosened the mast!",
            "The map says we're going the RIGHT way... trust me!",
            "Motor looks fine to me... *kicks it off*",
            "Waves? What waves? I paid the ocean to be calm!",
            "Bail faster or I'll make another hole for fun!",
        ]

    def update(self, boat, dt):
        self.sabotage_cooldown -= dt
        if self.sabotage_cooldown <= 0 and random.random() < 0.02:
            self.sabotage(boat)
            self.sabotage_cooldown = random.uniform(8, 15)

    def sabotage(self, boat):
        ev = random.choice(["mast","motor","hole","lost","wave"])
        if ev == "mast" and boat.mast_intact:
            boat.mast_intact = False
            mast_rip_sound.play()
            print("[DEBUG TIMMY] MAST RIPPED OFF!")
        elif ev == "motor" and boat.motor_intact:
            boat.motor_intact = False
            motor_fall_sound.play()
            print("[DEBUG TIMMY] MOTOR FELL OFF!")
        elif ev == "hole":
            boat.hole_count += 1
            hazard_sound.play()
            print("[DEBUG TIMMY] NEW HOLE!")
        elif ev == "lost":
            boat.x += random.randint(-80, 80)
            print("[DEBUG TIMMY] YOU'RE LOST!")
        elif ev == "wave":
            wave_crash_sound.play()
            print("[DEBUG TIMMY] GIANT WAVE! Timmy laughs!")

    def draw(self, surface, boat):
        tx = boat.x + 10
        ty = boat.y - 20
        pygame.draw.rect(surface, COLOR_TIMMY, (tx, ty, 14, 18))
        pygame.draw.circle(surface,(255,220,180),(tx+7, ty-4), 7)
        pygame.draw.arc(surface,(0,0,0),(tx+2,ty-9,10,6),0.2,3.0,2)
        pygame.draw.polygon(surface,(0,100,0),[(tx-2,ty-13),(tx+16,ty-13),(tx+7,ty-22)])


# ── Virtual button renderer ────────────────────────────────────────
def draw_vbuttons(surface, game_state, held):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    if game_state == 'TITLE':
        keys_to_draw = ['start']
    elif game_state == 'PLAYING':
        keys_to_draw = ['left','up','right','bail','repair','yell']
    else:
        keys_to_draw = []

    for k in keys_to_draw:
        rect   = VBTN[k]
        active = held.get(k, False)
        bg     = (255, 220, 50, 200) if active else (30, 100, 200, 140)
        border = (255, 255, 255, 220)
        pygame.draw.rect(overlay, bg,     rect)
        pygame.draw.rect(overlay, border, rect, 2)
        lbl = FONT_SMALL.render(VBTN_LABELS[k], True, (255,255,255))
        overlay.blit(lbl, (rect.centerx - lbl.get_width()//2,
                            rect.centery - lbl.get_height()//2))
    surface.blit(overlay, (0, 0))


# ====================== MAIN GAME ======================
def main():
    boat       = Boat()
    timmy      = CaptainTimmy()

    distance_traveled   = 0
    wind                = 0.0
    wave_phase          = 0.0
    game_state          = "TITLE"
    last_hazard_time    = time.time()
    timmy_dialogue_timer= 0
    current_dialogue    = ""
    music_index         = 0
    music_timer         = 0.0

    # Virtual button hold state
    held = {k: False for k in VBTN}
    # Touch ID → button name (multi-touch support)
    touch_map = {}

    print("[DEBUG GAME START] Boating with Timmy — Android edition!")
    print("[DEBUG] pygame:", pygame.version.ver, "  Android:", IS_ANDROID)

    while True:
        dt = clock.tick(FPS) / 1000.0

        # ── One-frame action flags ─────────────────────────────────
        do_bail   = False
        do_repair = False
        do_yell   = False
        do_start  = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # ── Keyboard ──────────────────────────────────────────
            if event.type == pygame.KEYDOWN:
                if game_state == 'TITLE' and event.key == pygame.K_RETURN:
                    do_start = True
                elif game_state == 'PLAYING':
                    if event.key == pygame.K_SPACE: do_bail   = True
                    if event.key == pygame.K_r:     do_repair = True
                    if event.key == pygame.K_m:     do_yell   = True
                elif game_state in ('WIN','LOSE'):
                    if event.key == pygame.K_r:
                        main(); return

            # ── Touch / Mouse DOWN ────────────────────────────────
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                if event.type == pygame.FINGERDOWN:
                    px = event.x * DISPLAY_W
                    py = event.y * DISPLAY_H
                    fid = event.finger_id
                else:
                    px, py = event.pos
                    fid = 'mouse'
                lx, ly = to_logical(px, py)
                pt = (lx, ly)

                if game_state == 'TITLE':
                    if VBTN['start'].collidepoint(pt) or True:
                        do_start = True          # tap anywhere starts
                elif game_state == 'PLAYING':
                    for k in ('left','up','right','bail','repair','yell'):
                        if VBTN[k].collidepoint(pt):
                            held[k] = True
                            touch_map[fid] = k
                            if k == 'bail':   do_bail   = True
                            if k == 'repair': do_repair = True
                            if k == 'yell':   do_yell   = True
                elif game_state in ('WIN','LOSE'):
                    main(); return

            # ── Touch / Mouse UP ──────────────────────────────────
            if event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
                fid = event.finger_id if event.type == pygame.FINGERUP else 'mouse'
                k   = touch_map.pop(fid, None)
                if k:
                    held[k] = False

            # ── Finger motion (drag between buttons) ──────────────
            if event.type == pygame.FINGERMOTION:
                px = event.x * DISPLAY_W
                py = event.y * DISPLAY_H
                lx, ly = to_logical(px, py)
                pt = (lx, ly)
                fid = event.finger_id
                old_k = touch_map.get(fid)
                new_k = None
                for k in ('left','up','right'):
                    if VBTN[k].collidepoint(pt):
                        new_k = k; break
                if old_k != new_k:
                    if old_k: held[old_k] = False
                    if new_k:
                        held[new_k]    = True
                        touch_map[fid] = new_k

        # ── State transitions ─────────────────────────────────────
        if do_start and game_state == 'TITLE':
            game_state = 'PLAYING'
            print("[DEBUG] Game started!")
            music_channel.play(create_sound(262,0.25,0.3))

        # ── Game logic ────────────────────────────────────────────
        keys = pygame.key.get_pressed()

        if game_state == 'PLAYING':
            # Movement — keyboard OR virtual buttons
            if keys[pygame.K_LEFT]  or held['left']:
                boat.angle -= 80 * dt
            if keys[pygame.K_RIGHT] or held['right']:
                boat.angle += 80 * dt
            if keys[pygame.K_UP] or held['up']:
                boat.speed  = min(BOAT_SPEED_MAX, boat.speed + 8 * dt)
                boat.fuel   = max(0, boat.fuel - 2 * dt)
            else:
                boat.speed  = max(0, boat.speed - 6 * dt)

            # One-shot actions
            if do_repair and boat.fuel > 10:
                boat.health      = min(100, boat.health + 25)
                boat.water_level = max(0, boat.water_level - 30)
                boat.fuel       -= 15
                repair_sound.play()
                print("[DEBUG] REPAIR activated")
            if do_bail:
                boat.water_level = max(0, boat.water_level - 25)
                splash_sound.play()
                print("[DEBUG] Bailing water")
            if do_yell:
                timmy_dialogue_timer = 1.5
                current_dialogue     = random.choice(timmy.dialogue)
                timmy_laugh_sound.play()
                print("[DEBUG] Yelled at Timmy")

            # Chiptune
            music_timer -= dt
            if music_timer <= 0:
                freq, dur = music_notes[music_index % len(music_notes)]
                music_channel.play(create_sound(freq, dur, 0.25))
                music_timer  = dur
                music_index += 1

            # Physics
            wave_phase += dt * 3
            wave = WAVE_AMPLITUDE * math.sin(wave_phase)
            wind = math.sin(pygame.time.get_ticks()/800)*1.5 + random.uniform(-0.5,0.5)
            boat.update(dt, wind, wave)
            timmy.update(boat, dt)

            distance_traveled += boat.speed * dt * 30
            if distance_traveled >= TARGET_DISTANCE:
                game_state = 'WIN'
                print("[DEBUG] YOU WIN! Timmy arrested.")

            # Random hazards
            if time.time() - last_hazard_time > random.uniform(4,12):
                hazard = random.choice(["big_wave","wind_gust","leak","timmy_kick"])
                if hazard == "big_wave":
                    boat.take_damage(12,"MASSIVE WAVE")
                    boat.water_level += 20
                    wave_crash_sound.play()
                elif hazard == "wind_gust":
                    boat.take_damage(8,"WIND GUST")
                    boat.angle += 30
                    hazard_sound.play()
                elif hazard == "leak":
                    boat.hole_count = min(4, boat.hole_count+1)
                    boat.take_damage(10,"NEW LEAK")
                    hazard_sound.play()
                elif hazard == "timmy_kick":
                    if boat.motor_intact or boat.mast_intact:
                        boat.take_damage(15,"TIMMY KICKED SOMETHING")
                        motor_fall_sound.play()
                last_hazard_time = time.time()

            if boat.water_level >= 100 or boat.health <= 0:
                game_state = 'LOSE'
                print("[DEBUG] CAPSIZED! Game over.")
            if boat.fuel <= 0:
                boat.speed = max(0, boat.speed - 3*dt)

        # ── Drawing ───────────────────────────────────────────────
        # Sky gradient
        for y in range(SCREEN_HEIGHT//2):
            shade = int(120 + (y/(SCREEN_HEIGHT//2))*60)
            pygame.draw.line(screen,(0,shade,255),(0,y),(SCREEN_WIDTH,y))
        # Water
        pygame.draw.rect(screen, COLOR_WATER,
                         (0, SCREEN_HEIGHT//2, SCREEN_WIDTH, SCREEN_HEIGHT//2))
        for i in range(12):
            wx = (i*60 + (pygame.time.get_ticks()//20)%120)%(SCREEN_WIDTH+100)-50
            wy = SCREEN_HEIGHT//2+40+int(WAVE_AMPLITUDE*math.sin(wave_phase+i))
            pygame.draw.line(screen,COLOR_WATER_DARK,(wx,wy),(wx+80,wy+8),4)

        if game_state == 'PLAYING':
            boat.draw(screen)
            timmy.draw(screen, boat)

        # Title screen
        if game_state == 'TITLE':
            ts = FONT_HUGE.render("BOATING WITH TIMMY", True, COLOR_TITLE)
            screen.blit(ts, (SCREEN_WIDTH//2-ts.get_width()//2, 45))
            for i,(text,col) in enumerate([
                ("REACH TREASURE ISLAND (5000 units) without capsizing!", COLOR_HUD),
                ("Hazards: waves, holes, Timmy sabotage!", (255,180,100)),
                ("",""),
                ("▲ = Accelerate    ◄ ► = Steer", COLOR_HUD),
                ("BAIL = Bail water    FIX = Repair (costs fuel)", COLOR_HUD),
                ("YELL = Yell at Timmy (he laughs)", COLOR_HUD),
            ]):
                s = FONT_SMALL.render(text, True, col)
                screen.blit(s,(SCREEN_WIDTH//2-s.get_width()//2, 130+i*22))

        # HUD
        if game_state == 'PLAYING':
            dist = FONT_LARGE.render(
                f"DIST: {int(distance_traveled)}/{TARGET_DISTANCE}", True, COLOR_HUD)
            screen.blit(dist,(10,10))
            # Health bar
            hcol = COLOR_HEALTH_GOOD if boat.health>40 else COLOR_HEALTH_BAD
            pygame.draw.rect(screen,(0,0,0),(10,40,202,18))
            pygame.draw.rect(screen,hcol,(12,42,int(boat.health*2),14))
            screen.blit(FONT_SMALL.render("HEALTH",True,COLOR_HUD),(15,43))
            # Water bar
            wcol = COLOR_WATER if boat.water_level>50 else (0,200,255)
            pygame.draw.rect(screen,(0,0,0),(10,62,202,18))
            pygame.draw.rect(screen,wcol,(12,64,int(boat.water_level*2),14))
            screen.blit(FONT_SMALL.render("WATER",True,COLOR_HUD),(15,65))
            # Fuel
            screen.blit(FONT_SMALL.render(f"FUEL:{int(boat.fuel)}%",True,COLOR_HUD),(10,84))
            # Status
            sy = 105
            if not boat.mast_intact:
                screen.blit(FONT_SMALL.render("MAST GONE!",True,(255,0,0)),(10,sy)); sy+=18
            if not boat.motor_intact:
                screen.blit(FONT_SMALL.render("MOTOR GONE!",True,(255,0,0)),(10,sy)); sy+=18
            if boat.hole_count:
                screen.blit(FONT_SMALL.render(f"{boat.hole_count} HOLES!",True,(255,100,0)),(10,sy))
            # Timmy dialogue
            if timmy_dialogue_timer > 0:
                timmy_dialogue_timer -= dt
                dlg = FONT_LARGE.render(current_dialogue, True,(255,255,100))
                # Wrap if too wide
                if dlg.get_width() > SCREEN_WIDTH-20:
                    dlg = FONT_SMALL.render(current_dialogue, True,(255,255,100))
                screen.blit(dlg,(SCREEN_WIDTH//2-dlg.get_width()//2, 330))

        # Win/Lose
        if game_state == 'WIN':
            s = FONT_HUGE.render("YOU MADE IT!", True,(0,255,0))
            screen.blit(s,(SCREEN_WIDTH//2-s.get_width()//2,160))
            s2 = FONT_LARGE.render("Timmy arrested. THE END.",True,COLOR_HUD)
            screen.blit(s2,(SCREEN_WIDTH//2-s2.get_width()//2,220))
            s3 = FONT_SMALL.render("Tap / press R to play again",True,COLOR_DEBUG)
            screen.blit(s3,(SCREEN_WIDTH//2-s3.get_width()//2,270))
        elif game_state == 'LOSE':
            s = FONT_HUGE.render("YOU CAPSIZED!", True,(255,0,0))
            screen.blit(s,(SCREEN_WIDTH//2-s.get_width()//2,160))
            s2 = FONT_LARGE.render("Timmy swims off with your wallet.",True,COLOR_HUD)
            screen.blit(s2,(SCREEN_WIDTH//2-s2.get_width()//2,220))
            s3 = FONT_SMALL.render("Tap / press R to play again",True,COLOR_DEBUG)
            screen.blit(s3,(SCREEN_WIDTH//2-s3.get_width()//2,270))

        # FPS debug
        fps_txt = FONT_SMALL.render(
            f"FPS:{int(clock.get_fps())} {game_state} WIND:{wind:.1f}", True, COLOR_DEBUG)
        screen.blit(fps_txt,(SCREEN_WIDTH-fps_txt.get_width()-4, SCREEN_HEIGHT-18))

        # Virtual buttons overlay
        draw_vbuttons(screen, game_state, held)

        # ── Scale to physical display & flip ──────────────────────
        if (DISPLAY_W, DISPLAY_H) != (SCREEN_WIDTH, SCREEN_HEIGHT):
            scaled = pygame.transform.scale(screen,(DISPLAY_W, DISPLAY_H))
            display.blit(scaled,(0,0))
        else:
            display.blit(screen,(0,0))
        pygame.display.flip()

        # Restart on win/lose
        if game_state in ('WIN','LOSE') and keys[pygame.K_r]:
            main(); return


if __name__ == "__main__":
    print("[DEBUG] Launching Boating with Timmy — Android edition!")
    main()
