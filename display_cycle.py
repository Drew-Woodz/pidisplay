import pygame
import os
import time

# Initialize Pygame with direct framebuffer access
os.putenv('SDL_VIDEODRIVER', 'directfb')  # Try directfb instead of fbcon
os.putenv('SDL_FBDEV', '/dev/fb0')       # Target the LCD framebuffer
pygame.init()
screen = pygame.display.set_mode((480, 320))  # Waveshare 3.5" resolution

# Create images folder if it doesn’t exist
image_folder = "images"
if not os.path.exists(image_folder):
    os.makedirs(image_folder)

# Load images
images = [f for f in os.listdir(image_folder) if f.endswith(".png")]
if not images:
    print("No PNGs found in images folder! Add some 480x320 PNGs.")
    exit()

# Main loop
while True:
    for img in images:
        image = pygame.image.load(os.path.join(image_folder, img))
        screen.blit(image, (0, 0))
        pygame.display.flip()
        time.sleep(30)  # Change every 30 seconds
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()