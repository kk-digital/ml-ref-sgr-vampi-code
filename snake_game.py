import pygame
import sys
import random

# Initialize Pygame
pygame.init()

# Constants
WIDTH = 640
HEIGHT = 480
BLOCK_SIZE = 20
FPS = 10

# Colors (RGB)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)

# Set up display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake Game")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 25)
large_font = pygame.font.SysFont("Arial", 50)

def get_random_food_pos(snake):
    """Generate random food position not on snake."""
    while True:
        x = random.randint(0, (WIDTH - BLOCK_SIZE) // BLOCK_SIZE) * BLOCK_SIZE
        y = random.randint(0, (HEIGHT - BLOCK_SIZE) // BLOCK_SIZE) * BLOCK_SIZE
        if (x, y) not in snake:
            return (x, y)

def draw_snake(screen, snake):
    """Draw the snake."""
    for block in snake:
        pygame.draw.rect(screen, GREEN, (block[0], block[1], BLOCK_SIZE, BLOCK_SIZE))
        pygame.draw.rect(screen, BLACK, (block[0], block[1], BLOCK_SIZE, BLOCK_SIZE), 1)

def draw_food(screen, food):
    """Draw the food."""
    pygame.draw.rect(screen, RED, (food[0], food[1], BLOCK_SIZE, BLOCK_SIZE))

def draw_score(screen, score):
    """Draw the score."""
    text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(text, (10, 10))

def draw_start_screen(screen):
    """Draw the start screen."""
    screen.fill(BLACK)
    title = large_font.render("Snake Game", True, GREEN)
    start_text = font.render("Press SPACE to start", True, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 50))
    screen.blit(start_text, (WIDTH//2 - start_text.get_width()//2, HEIGHT//2 + 10))
    pygame.display.flip()

def draw_game_over_screen(screen, score):
    """Draw the game over screen."""
    screen.fill(BLACK)
    game_over = large_font.render("Game Over", True, RED)
    score_text = font.render(f"Final Score: {score}", True, WHITE)
    restart_text = font.render("Press SPACE to restart or ESC to quit", True, WHITE)
    screen.blit(game_over, (WIDTH//2 - game_over.get_width()//2, HEIGHT//2 - 50))
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, HEIGHT//2))
    screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 40))
    pygame.display.flip()

def main():
    """Main game loop."""
    # Game state
    state = "start"  # start, play, game_over
    snake = [(WIDTH//2, HEIGHT//2)]
    direction = (0, 0)  # (dx, dy)
    food = get_random_food_pos(snake)
    score = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if state == "start":
                    if event.key == pygame.K_SPACE:
                        state = "play"
                elif state == "play":
                    if event.key == pygame.K_UP and direction != (0, BLOCK_SIZE):
                        direction = (0, -BLOCK_SIZE)
                    elif event.key == pygame.K_DOWN and direction != (0, -BLOCK_SIZE):
                        direction = (0, BLOCK_SIZE)
                    elif event.key == pygame.K_LEFT and direction != (BLOCK_SIZE, 0):
                        direction = (-BLOCK_SIZE, 0)
                    elif event.key == pygame.K_RIGHT and direction != (-BLOCK_SIZE, 0):
                        direction = (BLOCK_SIZE, 0)
                elif state == "game_over":
                    if event.key == pygame.K_SPACE:
                        # Restart
                        snake = [(WIDTH//2, HEIGHT//2)]
                        direction = (0, 0)
                        food = get_random_food_pos(snake)
                        score = 0
                        state = "play"
                    elif event.key == pygame.K_ESCAPE:
                        running = False

        if state == "start":
            draw_start_screen(screen)
            continue

        if state == "game_over":
            draw_game_over_screen(screen, score)
            continue

        # Update snake
        head = snake[0]
        new_head = (head[0] + direction[0], head[1] + direction[1])

        # Check wall collision
        if (new_head[0] < 0 or new_head[0] >= WIDTH or
            new_head[1] < 0 or new_head[1] >= HEIGHT):
            state = "game_over"
            continue

        # Check self collision
        if new_head in snake:
            state = "game_over"
            continue

        snake.insert(0, new_head)

        # Check food collision
        if new_head == food:
            score += 1
            food = get_random_food_pos(snake)
        else:
            snake.pop()

        # Draw everything
        screen.fill(BLACK)
        draw_snake(screen, snake)
        draw_food(screen, food)
        draw_score(screen, score)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
