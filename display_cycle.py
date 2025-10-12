# display_cycle.py
import os, sys, time, glob
import pygame
from pygame import transform

# --- Config ---
WIDTH, HEIGHT = 480, 320
IMAGE_DIR = os.environ.get("IMAGE_DIR", os.path.join(os.path.dirname(__file__), "images"))
INTERVAL = float(os.environ.get("SLIDE_INTERVAL", "10"))  # seconds
FULLSCREEN_FLAGS = pygame.FULLSCREEN

# --- Force SDL to the SPI framebuffer ---
os.environ.setdefault("SDL_VIDEODRIVER", "fbcon")
os.environ.setdefault("SDL_FBDEV", "/dev/fb1")

def list_images():
    exts = (".png", ".jpg", ".jpeg", ".bmp")
    files = [p for p in sorted(glob.glob(os.path.join(IMAGE_DIR, "*"))) if p.lower().endswith(exts)]
    return files

def load_fit_center(path, w, h):
    """Load with pygame only (no Pillow dependency), letterbox to (w,h)."""
    img = pygame.image.load(path).convert()  # convert to display format for speed
    iw, ih = img.get_size()
    # scale to fit inside (w,h) while preserving aspect
    scale = min(w / iw, h / ih)
    new_w, new_h = max(1, int(iw * scale)), max(1, int(ih * scale))
    surf = transform.smoothscale(img, (new_w, new_h)) if (new_w, new_h) != (iw, ih) else img
    # letterbox onto a black canvas
    canvas = pygame.Surface((w, h))
    canvas.fill((0, 0, 0))
    canvas.blit(surf, ((w - new_w) // 2, (h - new_h) // 2))
    return canvas

def main():
    # Init display
    pygame.display.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), FULLSCREEN_FLAGS)
    clock = pygame.time.Clock()

    files = list_images()
    if not files:
        screen.fill((0, 0, 0))
        pygame.display.update()
        print(f"No images in {IMAGE_DIR}. Add PNG/JPG files.")
        time.sleep(5)
        return

    idx = 0
    while True:
        # Soft-reload the directory each cycle so you can add/remove files live
        files = list_images() or files
        path = files[idx % len(files)]

        # Render one image
        try:
            frame = load_fit_center(path, WIDTH, HEIGHT)
            screen.blit(frame, (0, 0))
            pygame.display.update()
        except Exception as e:
            # draw an error banner; keep going
            screen.fill((10, 0, 0))
            err = f"Error: {os.path.basename(path)}"
            pygame.display.set_caption(err)
            pygame.display.update()

        # Wait with a small event pump so QUIT works if you ever run under X
        t0 = time.time()
        while time.time() - t0 < INTERVAL:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
            clock.tick(30)

        idx += 1

if __name__ == "__main__":
    try:
        main()
    finally:
        pygame.quit()
