import pygame
import sys
import random

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BLOCK_SIZE = 20
SNAKE_SPEED = 10

# Colors (RGB)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)

# Directions
UP = (0, -BLOCK_SIZE)
DOWN = (0, BLOCK_SIZE)
LEFT = (-BLOCK_SIZE, 0)
RIGHT = (BLOCK_SIZE, 0)

class SnakeGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('Snake Game')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 35)
        self.big_font = pygame.font.SysFont(None, 50)
        
        self.reset_game()
    
    def reset_game(self):
        self.snake = [(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)]
        self.direction = RIGHT
        self.food = self.generate_food()
        self.score = 0
        self.game_state = 'start'  # 'start', 'playing', 'game_over'
    
    def generate_food(self):
        while True:
            food = (random.randint(0, (SCREEN_WIDTH - BLOCK_SIZE) // BLOCK_SIZE) * BLOCK_SIZE,
                    random.randint(0, (SCREEN_HEIGHT - BLOCK_SIZE) // BLOCK_SIZE) * BLOCK_SIZE)
            if food not in self.snake:
                return food
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if self.game_state == 'playing':
                    if event.key == pygame.K_UP and self.direction != DOWN:
                        self.direction = UP
                    elif event.key == pygame.K_DOWN and self.direction != UP:
                        self.direction = DOWN
                    elif event.key == pygame.K_LEFT and self.direction != RIGHT:
                        self.direction = LEFT
                    elif event.key == pygame.K_RIGHT and self.direction != LEFT:
                        self.direction = RIGHT
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        if self.game_state == 'start':
                            self.reset_game()
                            self.game_state = 'playing'
                        elif self.game_state == 'game_over':
                            self.reset_game()
                            self.game_state = 'playing'
        return True
    
    def update_snake(self):
        head = (self.snake[0][0] + self.direction[0], self.snake[0][1] + self.direction[1])
        
        # Check wall collision
        if (head[0] < 0 or head[0] >= SCREEN_WIDTH or 
            head[1] < 0 or head[1] >= SCREEN_HEIGHT):
            self.game_state = 'game_over'
            return
        
        # Check self collision
        if head in self.snake:
            self.game_state = 'game_over'
            return
        
        self.snake.insert(0, head)
        
        # Check food collision
        if head == self.food:
            self.score += 10
            self.food = self.generate_food()
        else:
            self.snake.pop()
    
    def draw_snake(self):
        for segment in self.snake:
            pygame.draw.rect(self.screen, GREEN, (segment[0], segment[1], BLOCK_SIZE, BLOCK_SIZE))
    
    def draw_food(self):
        pygame.draw.rect(self.screen, RED, (self.food[0], self.food[1], BLOCK_SIZE, BLOCK_SIZE))
    
    def show_score(self):
        score_text = self.font.render(f'Score: {self.score}', True, WHITE)
        self.screen.blit(score_text, (10, 10))
    
    def start_screen(self):
        self.screen.fill(BLACK)
        title = self.big_font.render('Snake Game', True, GREEN)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(title, title_rect)
        
        instruction = self.font.render('Press SPACE to start', True, WHITE)
        inst_rect = instruction.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(instruction, inst_rect)
    
    def game_over_screen(self):
        self.screen.fill(BLACK)
        game_over = self.big_font.render('Game Over', True, RED)
        go_rect = game_over.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(game_over, go_rect)
        
        final_score = self.font.render(f'Final Score: {self.score}', True, WHITE)
        fs_rect = final_score.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(final_score, fs_rect)
        
        restart = self.font.render('Press SPACE to play again', True, WHITE)
        r_rect = restart.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(restart, r_rect)
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            
            if self.game_state == 'playing':
                self.update_snake()
            
            self.screen.fill(BLACK)
            
            if self.game_state == 'start':
                self.start_screen()
            elif self.game_state == 'playing':
                self.draw_snake()
                self.draw_food()
                self.show_score()
            elif self.game_state == 'game_over':
                self.game_over_screen()
            
            pygame.display.flip()
            self.clock.tick(SNAKE_SPEED)
        
        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    game = SnakeGame()
    game.run()