import pygame
import numpy as np

# defining some constants for the visualization
WIDTH = 800
HEIGHT = 600
FPS = 30
N_PARTICLES = 1000
SIGMA = 2.0

# initialize pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sonic Brownian Motion Visualization")
clock = pygame.time.Clock()

# initialize particle
rng = np.random.default_rng(1)
positions = rng.uniform(low=[0, 0], high=[WIDTH, HEIGHT], size=(N_PARTICLES, 2))

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    noise = rng.standard_normal(size=(N_PARTICLES, 2))
    positions += SIGMA * noise

    positions[:, 0] %= WIDTH
    positions[:, 1] %= HEIGHT

    screen.fill((0, 0, 0))

    for x, y in positions: # draw each particle as a small circle
        pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), 2)

    pygame.display.flip()
    clock.tick(FPS)
    
pygame.quit()
