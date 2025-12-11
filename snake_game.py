"""
Snake Game - A classic arcade game implemented in Python using Pygame

Controls:
    - Arrow keys to move the snake
    - Press any key to start/restart the game
    - ESC to quit

Author: AI Assistant
"""

import pygame
import random
import sys
from enum import Enum
from typing import List, Tuple

# Initialize Pygame
pygame.init()

# =============================================================================
# GAME CONSTANTS
# =============================================================================

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Grid settings
CELL_SIZE = 20
GRID_WIDTH = SCREEN_WIDTH // CELL_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // CELL_SIZE

# Colors (RGB)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
DARK_GREEN = (0, 200, 0)
RED = (255, 0, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (40, 40, 40)

# Game settings
FPS = 10  # Snake speed (frames per second)
INITIAL_SNAKE_LENGTH = 3


# =============================================================================
# DIRECTION ENUM
# =============================================================================

class Direction(Enum):
    """Enum representing the four possible movement directions."""
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


# =============================================================================
# SNAKE CLASS
# =============================================================================

class Snake:
    """Represents the snake in the game."""
    
    def __init__(self):
        """Initialize the snake at the center of the screen."""
        self.reset()
    
    def reset(self) -> None:
        """Reset the snake to its initial state."""
        # Start at the center of the grid
        start_x = GRID_WIDTH // 2
        start_y = GRID_HEIGHT // 2
        
        # Create initial snake body (head + tail segments)
        self.body: List[Tuple[int, int]] = []
        for i in range(INITIAL_SNAKE_LENGTH):
            self.body.append((start_x - i, start_y))
        
        # Initial direction is right
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.growing = False
    
    @property
    def head(self) -> Tuple[int, int]:
        """Return the position of the snake's head."""
        return self.body[0]
    
    def change_direction(self, new_direction: Direction) -> None:
        """
        Change the snake's direction if it's not opposite to current direction.
        
        Args:
            new_direction: The new direction to move in
        """
        # Prevent 180-degree turns (can't go directly opposite)
        opposites = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT
        }
        
        if new_direction != opposites.get(self.direction):
            self.next_direction = new_direction
    
    def move(self) -> None:
        """Move the snake one cell in the current direction."""
        # Update direction
        self.direction = self.next_direction
        
        # Calculate new head position
        dx, dy = self.direction.value
        new_head = (self.head[0] + dx, self.head[1] + dy)
        
        # Insert new head at the beginning
        self.body.insert(0, new_head)
        
        # Remove tail unless growing
        if not self.growing:
            self.body.pop()
        else:
            self.growing = False
    
    def grow(self) -> None:
        """Mark the snake to grow on the next move."""
        self.growing = True
    
    def check_collision_with_self(self) -> bool:
        """Check if the snake has collided with itself."""
        return self.head in self.body[1:]
    
    def check_collision_with_wall(self) -> bool:
        """Check if the snake has collided with the wall."""
        x, y = self.head
        return x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT
    
    def draw(self, screen: pygame.Surface) -> None:
        """
        Draw the snake on the screen.
        
        Args:
            screen: The pygame surface to draw on
        """
        for i, segment in enumerate(self.body):
            x = segment[0] * CELL_SIZE
            y = segment[1] * CELL_SIZE
            
            # Draw head in a different shade
            if i == 0:
                color = GREEN
            else:
                color = DARK_GREEN
            
            # Draw the segment with a small border for visual separation
            rect = pygame.Rect(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2)
            pygame.draw.rect(screen, color, rect)
            
            # Add eyes to the head
            if i == 0:
                self._draw_eyes(screen, x, y)
    
    def _draw_eyes(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Draw eyes on the snake's head based on direction."""
        eye_size = 4
        eye_color = BLACK
        
        # Calculate eye positions based on direction
        if self.direction == Direction.RIGHT:
            eye1_pos = (x + CELL_SIZE - 6, y + 5)
            eye2_pos = (x + CELL_SIZE - 6, y + CELL_SIZE - 9)
        elif self.direction == Direction.LEFT:
            eye1_pos = (x + 4, y + 5)
            eye2_pos = (x + 4, y + CELL_SIZE - 9)
        elif self.direction == Direction.UP:
            eye1_pos = (x + 5, y + 4)
            eye2_pos = (x + CELL_SIZE - 9, y + 4)
        else:  # DOWN
            eye1_pos = (x + 5, y + CELL_SIZE - 6)
            eye2_pos = (x + CELL_SIZE - 9, y + CELL_SIZE - 6)
        
        pygame.draw.circle(screen, eye_color, eye1_pos, eye_size // 2)
        pygame.draw.circle(screen, eye_color, eye2_pos, eye_size // 2)


# =============================================================================
# FOOD CLASS
# =============================================================================

class Food:
    """Represents the food that the snake eats."""
    
    def __init__(self):
        """Initialize food at a random position."""
        self.position: Tuple[int, int] = (0, 0)
        self.spawn()
    
    def spawn(self, snake_body: List[Tuple[int, int]] = None) -> None:
        """
        Spawn food at a random position not occupied by the snake.
        
        Args:
            snake_body: List of positions occupied by the snake
        """
        if snake_body is None:
            snake_body = []
        
        while True:
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            
            if (x, y) not in snake_body:
                self.position = (x, y)
                break
    
    def draw(self, screen: pygame.Surface) -> None:
        """
        Draw the food on the screen.
        
        Args:
            screen: The pygame surface to draw on
        """
        x = self.position[0] * CELL_SIZE
        y = self.position[1] * CELL_SIZE
        
        # Draw food as a red circle
        center = (x + CELL_SIZE // 2, y + CELL_SIZE // 2)
        radius = CELL_SIZE // 2 - 2
        pygame.draw.circle(screen, RED, center, radius)
        
        # Add a small highlight for 3D effect
        highlight_pos = (center[0] - 3, center[1] - 3)
        pygame.draw.circle(screen, (255, 100, 100), highlight_pos, 3)


# =============================================================================
# GAME CLASS
# =============================================================================

class Game:
    """Main game class that handles game logic and rendering."""
    
    def __init__(self):
        """Initialize the game."""
        # Set up the display
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Snake Game")
        
        # Set up the clock for controlling frame rate
        self.clock = pygame.time.Clock()
        
        # Set up fonts
        self.font_large = pygame.font.Font(None, 74)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)
        
        # Initialize game objects
        self.snake = Snake()
        self.food = Food()
        
        # Game state
        self.score = 0
        self.high_score = 0
        self.game_state = "start"  # "start", "playing", "game_over"
    
    def reset_game(self) -> None:
        """Reset the game to its initial state."""
        self.snake.reset()
        self.food.spawn(self.snake.body)
        self.score = 0
        self.game_state = "playing"
    
    def handle_events(self) -> bool:
        """
        Handle pygame events.
        
        Returns:
            False if the game should quit, True otherwise
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                
                # Handle different game states
                if self.game_state == "start":
                    self.reset_game()
                
                elif self.game_state == "playing":
                    # Handle direction changes
                    if event.key == pygame.K_UP:
                        self.snake.change_direction(Direction.UP)
                    elif event.key == pygame.K_DOWN:
                        self.snake.change_direction(Direction.DOWN)
                    elif event.key == pygame.K_LEFT:
                        self.snake.change_direction(Direction.LEFT)
                    elif event.key == pygame.K_RIGHT:
                        self.snake.change_direction(Direction.RIGHT)
                
                elif self.game_state == "game_over":
                    # Any key restarts the game
                    self.reset_game()
        
        return True
    
    def update(self) -> None:
        """Update game logic."""
        if self.game_state != "playing":
            return
        
        # Move the snake
        self.snake.move()
        
        # Check for collisions with walls or self
        if self.snake.check_collision_with_wall() or self.snake.check_collision_with_self():
            self.game_state = "game_over"
            if self.score > self.high_score:
                self.high_score = self.score
            return
        
        # Check if snake ate food
        if self.snake.head == self.food.position:
            self.snake.grow()
            self.score += 10
            self.food.spawn(self.snake.body)
    
    def draw_grid(self) -> None:
        """Draw a subtle grid on the background."""
        for x in range(0, SCREEN_WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, DARK_GRAY, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, CELL_SIZE):
            pygame.draw.line(self.screen, DARK_GRAY, (0, y), (SCREEN_WIDTH, y))
    
    def draw_score(self) -> None:
        """Draw the current score on the screen."""
        score_text = self.font_small.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        
        # Draw high score
        high_score_text = self.font_small.render(f"High Score: {self.high_score}", True, GRAY)
        self.screen.blit(high_score_text, (SCREEN_WIDTH - high_score_text.get_width() - 10, 10))
    
    def draw_start_screen(self) -> None:
        """Draw the start screen."""
        self.screen.fill(BLACK)
        
        # Title
        title = self.font_large.render("SNAKE GAME", True, GREEN)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.screen.blit(title, title_rect)
        
        # Instructions
        instructions = [
            "Use ARROW KEYS to move",
            "Eat the RED food to grow",
            "Don't hit the walls or yourself!",
            "",
            "Press any key to start"
        ]
        
        y_offset = SCREEN_HEIGHT // 2
        for line in instructions:
            text = self.font_small.render(line, True, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
            self.screen.blit(text, text_rect)
            y_offset += 40
        
        # Draw a sample snake
        sample_snake_x = SCREEN_WIDTH // 2 - 40
        sample_snake_y = SCREEN_HEIGHT // 3 + 60
        for i in range(3):
            color = GREEN if i == 0 else DARK_GREEN
            rect = pygame.Rect(sample_snake_x + i * CELL_SIZE, sample_snake_y, 
                             CELL_SIZE - 2, CELL_SIZE - 2)
            pygame.draw.rect(self.screen, color, rect)
    
    def draw_game_over_screen(self) -> None:
        """Draw the game over screen."""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(200)
        self.screen.blit(overlay, (0, 0))
        
        # Game Over text
        game_over_text = self.font_large.render("GAME OVER", True, RED)
        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.screen.blit(game_over_text, game_over_rect)
        
        # Final score
        score_text = self.font_medium.render(f"Final Score: {self.score}", True, WHITE)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(score_text, score_rect)
        
        # High score
        if self.score >= self.high_score and self.score > 0:
            high_score_text = self.font_medium.render("NEW HIGH SCORE!", True, GREEN)
        else:
            high_score_text = self.font_small.render(f"High Score: {self.high_score}", True, GRAY)
        high_score_rect = high_score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(high_score_text, high_score_rect)
        
        # Restart instruction
        restart_text = self.font_small.render("Press any key to play again", True, WHITE)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 2 // 3))
        self.screen.blit(restart_text, restart_rect)
    
    def draw(self) -> None:
        """Draw the current game state."""
        if self.game_state == "start":
            self.draw_start_screen()
        
        elif self.game_state == "playing":
            self.screen.fill(BLACK)
            self.draw_grid()
            self.food.draw(self.screen)
            self.snake.draw(self.screen)
            self.draw_score()
        
        elif self.game_state == "game_over":
            # Draw the game state behind the overlay
            self.screen.fill(BLACK)
            self.draw_grid()
            self.food.draw(self.screen)
            self.snake.draw(self.screen)
            self.draw_game_over_screen()
        
        pygame.display.flip()
    
    def run(self) -> None:
        """Main game loop."""
        running = True
        
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main function to start the game."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
