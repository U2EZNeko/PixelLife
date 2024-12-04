# cell_simulation.py

import pygame
import random
import math

# Constants
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
CELL_SIZE = 10
GRID_CELL_SIZE = CELL_SIZE * 3
TICK_RATE = 30

# Game Variables
NUM_INITIAL_CELLS = 50
NUM_INITIAL_FOOD = 200
FOOD_RESPAWN_RATE = 0.3
STAMINA_PER_STEP = 0.25
FOOD_GAINED_FROM_FOOD_CELLS = 45
STAMINA_GAINED_FROM_FOOD_CELLS = 45
IDLE_STAMINA_GAIN = 0.5
IDLE_HUNGER_CONSUMPTION = 0.1

# Obstacles
NUM_OBSTACLES = 10
MAX_OBSTACLE_WIDTH = 100
MAX_OBSTACLE_HEIGHT = 100

# Graph data
live_cells_history = []
food_cells_history = []
highest_generation_history = []
ticks = []

# Mating Data
MATING_STAMINA_COST = 90
MATING_HUNGER_COST = 30
MATING_COOLDOWN = 400
MATING_DURATION = 240
NEWBORN_MATING_COOLDOWN = 160

# Cell stats
MAX_HP = 100
MAX_STAMINA = 150
MAX_HUNGER = 150
CELL_INITIAL_HP = 100
CELL_INITIAL_STAMINA = 150
CELL_INITIAL_HUNGER = 120
MAX_AGE = 1400
INITIAL_MORTALITY_CHANCE = 0.0000

# Food limits
MAX_FOOD_CELLS = 300
MIN_FOOD_CELLS = 50

# Colors
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
PINK = (255, 125, 215)
BLUE = (0, 0, 255)
CYAN = (0, 120, 155)
RED = (255, 0, 0)
ORANGE = (200, 100, 0)
HOT_PINK = (255, 0, 166)
GRAY = (110, 110, 110)
YELLOW = (255, 255, 102)

class SpatialGrid:
    def __init__(self, width, height, cell_size):
        self.cell_size = cell_size
        self.width = width // cell_size + 1
        self.height = height // cell_size + 1
        self.grid = [[[] for _ in range(self.height)] for _ in range(self.width)]

    def add(self, cell):
        x_idx = int(cell.x // self.cell_size)
        y_idx = int(cell.y // self.cell_size)
        self.grid[x_idx][y_idx].append(cell)

    def remove(self, cell):
        x_idx = int(cell.x // self.cell_size)
        y_idx = int(cell.y // self.cell_size)
        self.grid[x_idx][y_idx].remove(cell)

    def move(self, cell, old_x, old_y):
        old_x_idx = int(old_x // self.cell_size)
        old_y_idx = int(old_y // self.cell_size)
        new_x_idx = int(cell.x // self.cell_size)
        new_y_idx = int(cell.y // self.cell_size)
        if old_x_idx != new_x_idx or old_y_idx != new_y_idx:
            self.grid[old_x_idx][old_y_idx].remove(cell)
            self.grid[new_x_idx][new_y_idx].append(cell)

    def get_nearby(self, x, y):
        x_idx = int(x // self.cell_size)
        y_idx = int(y // self.cell_size)
        cells = []
        for i in range(max(0, x_idx-1), min(self.width, x_idx+2)):
            for j in range(max(0, y_idx-1), min(self.height, y_idx+2)):
                cells.extend(self.grid[i][j])
        return cells

class Cell:
    def __init__(self, x, y, generation=0):
        self.hp = min(CELL_INITIAL_HP, MAX_HP)
        self.hunger = min(CELL_INITIAL_HUNGER, MAX_HUNGER)
        self.stamina = min(CELL_INITIAL_STAMINA, MAX_STAMINA)
        self.x = x
        self.y = y
        self.mating_cooldown = NEWBORN_MATING_COOLDOWN
        self.mating_timer = 0
        self.is_mating = False
        self.age = 0
        self.mortality_chance = INITIAL_MORTALITY_CHANCE
        self.is_dead = False
        self.generation = generation
        self.speed = random.randint(-1, 1)
        self.max_hp = random.randint(-1, 1)
        self.max_stamina = random.randint(-1, 1)
        self.max_hunger = random.randint(-1, 1)
        self.direction_x = 0  # Initialize to zero
        self.direction_y = 0  # Initialize to zero

    def move_towards(self, target_x, target_y, spatial_grid, obstacles):
        if self.stamina > 0:
            self.stamina -= STAMINA_PER_STEP * calculate_energy_multiplier(self)  # Apply multiplier
            direction_x = target_x - self.x
            direction_y = target_y - self.y
            distance_to_target = (direction_x ** 2 + direction_y ** 2) ** 0.5
            step_size = CELL_SIZE * (self.speed if self.speed > 0 else 1)
            if distance_to_target < step_size:
                step_size = distance_to_target
            if distance_to_target > 0:
                direction_x /= distance_to_target
                direction_y /= distance_to_target
                # Store the normalized direction
                self.direction_x = direction_x
                self.direction_y = direction_y
            old_x, old_y = self.x, self.y
            new_x = self.x + direction_x * step_size
            new_y = self.y + direction_y * step_size
            new_x = max(min(new_x, SCREEN_WIDTH - CELL_SIZE), 0)
            new_y = max(min(new_y, SCREEN_HEIGHT - CELL_SIZE), 0)
            if not self.is_collision(new_x, new_y, spatial_grid, obstacles):
                self.x, self.y = new_x, new_y
                spatial_grid.move(self, old_x, old_y)
        else:
            self.stamina = min(self.stamina + IDLE_STAMINA_GAIN, CELL_INITIAL_STAMINA)
        self.hunger += IDLE_HUNGER_CONSUMPTION

    def move(self, food_cells, spatial_grid, obstacles):
        if self.is_mating:
            return
        if self.hunger <= 0:
            self.hp -= 0.5
        if self.hunger >= 90:
            self.hp += 1
        if self.stamina >= 0:
            if self.hunger <= 90:
                nearest_food = self.find_nearest(food_cells)
                if nearest_food:
                    self.move_towards(nearest_food.x, nearest_food.y, spatial_grid, obstacles)
            elif self.hunger >= 90 and self.hp >= 90 and self.mating_cooldown == 0:
                nearest_mate = self.find_nearest_mate(spatial_grid.get_nearby(self.x, self.y))
                if nearest_mate:
                    self.move_towards(nearest_mate.x, nearest_mate.y, spatial_grid, obstacles)
            else:
                if random.random() < 0.5:
                    return
                else:
                    self.move_randomly(spatial_grid, obstacles)
            self.stamina -= STAMINA_PER_STEP
        else:
            self.stamina = min(self.stamina + IDLE_STAMINA_GAIN, MAX_STAMINA)

    def move_randomly(self, spatial_grid, obstacles):
        if self.stamina > 0:
            self.stamina -= STAMINA_PER_STEP * calculate_energy_multiplier(self)  # Apply multiplier
        directions = ['up', 'down', 'left', 'right']
        random.shuffle(directions)
        for direction in directions:
            new_x, new_y = self.x, self.y
            step_size = CELL_SIZE * (self.speed if self.speed > 0 else 1)
            if direction == 'up' and self.y > 0:
                new_y -= step_size
                self.direction_x = 0
                self.direction_y = -1
            elif direction == 'down' and self.y < SCREEN_HEIGHT - CELL_SIZE:
                new_y += step_size
                self.direction_x = 0
                self.direction_y = 1
            elif direction == 'left' and self.x > 0:
                new_x -= step_size
                self.direction_x = -1
                self.direction_y = 0
            elif direction == 'right' and self.x < SCREEN_WIDTH - CELL_SIZE:
                new_x += step_size
                self.direction_x = 1
                self.direction_y = 0
            else:
                continue  # Skip invalid movement
            if self.is_within_bounds(new_x, new_y) and not self.is_collision(new_x, new_y, spatial_grid, obstacles):
                old_x, old_y = self.x, self.y
                self.x, self.y = new_x, new_y
                spatial_grid.move(self, old_x, old_y)
                break

    def is_within_bounds(self, x, y):
        return 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT

    def find_nearest(self, objects):
        nearest_object = None
        min_distance = float('inf')
        for obj in objects:
            if obj.x != -1 and obj.y != -1:
                distance = math.hypot(self.x - obj.x, self.y - obj.y)
                if distance < min_distance:
                    min_distance = distance
                    nearest_object = obj
        return nearest_object

    def find_nearest_mate(self, cells):
        #print("A cell is looking for mate.")
        nearest_mate = None
        min_distance = float('inf')
        for cell in cells:
            if cell != self and cell.hunger == CELL_INITIAL_HUNGER and cell.hp == CELL_INITIAL_HP and cell.mating_cooldown == 0 and not cell.is_mating:
                distance = math.hypot(self.x - cell.x, self.y - cell.y)
                if distance < min_distance:
                    min_distance = distance
                    nearest_mate = cell
                    print("A cell has found a mate.")
        return nearest_mate

    def start_mating(self, other):
        print("Cell is Mating.")
        self.is_mating = True
        self.mating_timer = MATING_DURATION
        other.is_mating = True
        other.mating_timer = MATING_DURATION

    def mate(self, other, spatial_grid, obstacles):
        if self.mating_timer > 0:
            self.mating_timer -= 1
            other.mating_timer -= 1
            return []
        self.stamina -= MATING_STAMINA_COST
        self.hunger -= MATING_HUNGER_COST
        other.stamina -= MATING_STAMINA_COST
        other.hunger -= MATING_HUNGER_COST
        offspring = []
        num_offspring = random.randint(1, 3)
        for _ in range(num_offspring):
            for _ in range(10):  # Try up to 10 times to find a valid position
                new_x = self.x + random.choice([-CELL_SIZE, 0, CELL_SIZE])
                new_y = self.y + random.choice([-CELL_SIZE, 0, CELL_SIZE])
                if self.is_within_bounds(new_x, new_y) and not self.is_collision(new_x, new_y, spatial_grid, obstacles):
                    new_cell = Cell(new_x, new_y, self.generation + 1)
                    new_cell.mating_cooldown = NEWBORN_MATING_COOLDOWN
                    # Traits with mutations
                    new_cell.speed = max(1, (self.speed + other.speed) // 2 + random.randint(-1, 1))
                    new_cell.max_hp = max(10, (self.max_hp + other.max_hp) // 2 + random.randint(-2, 2))
                    new_cell.max_stamina = max(10, (self.max_stamina + other.max_stamina) // 2 + random.randint(-2, 2))
                    new_cell.max_hunger = max(10, (self.max_hunger + other.max_hunger) // 2 + random.randint(-2, 2))
                    offspring.append(new_cell)
                    spatial_grid.add(new_cell)
                    print("A cell has been spawned:" "MAX_HP:" + str(self.max_hp) + " Max Hunger:" + str(
                        self.max_hunger) + " Max Stam:" + str(self.max_stamina))
                    break
        self.is_mating = False
        self.mating_cooldown = MATING_COOLDOWN
        other.is_mating = False
        other.mating_cooldown = MATING_COOLDOWN
        return offspring

    def eat(self, food, food_cells):
        if self.hunger < MAX_HUNGER:
            self.hunger = min(self.hunger + FOOD_GAINED_FROM_FOOD_CELLS, MAX_HUNGER)
            food_cells.remove(food)
        elif self.hunger == MAX_HUNGER:
            self.stamina = min(self.stamina + STAMINA_GAINED_FROM_FOOD_CELLS, MAX_STAMINA)

    def update_status(self):
        self.age += 1
        if self.age > 0.7 * MAX_AGE:
            self.mortality_chance += 0.0001
        if random.random() < self.mortality_chance:
            self.hp = 0
            print("A cell has died")
        self.hunger -= 1
        if self.hunger <= 0:
            self.hp -= 1
        if self.hunger >= 100:
            self.hp += 1
        if self.hp > MAX_HP:
            self.hp = MAX_HP
        if self.mating_cooldown > 0:
            self.mating_cooldown -= 1
        if self.stamina < MAX_STAMINA:
            self.stamina = min(self.stamina + IDLE_STAMINA_GAIN, MAX_STAMINA)
        if self.stamina > MAX_STAMINA:
            self.stamina = MAX_STAMINA
        if self.hp <= 0:
            self.is_dead = True

    def is_collision(self, x, y, spatial_grid, obstacles):
        # Check obstacle collisions
        for obstacle in obstacles:
            if obstacle.is_collision(x, y):
                return True
        # Check cell collisions
        nearby_cells = spatial_grid.get_nearby(x, y)
        for cell in nearby_cells:
            if cell != self and cell.x == x and cell.y == y:
                return True
        return False

    def is_adjacent(self, other):
        return abs(self.x - other.x) <= CELL_SIZE and abs(self.y - other.y) <= CELL_SIZE

class Food:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def consume(self):
        self.x, self.y = -1, -1

class Obstacle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def is_collision(self, x, y):
        """Check if a given point collides with the obstacle."""
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

def generate_random_obstacles(num_obstacles, max_width, max_height):
    obstacles = []
    for _ in range(num_obstacles):
        width = random.randint(20, max_width)
        height = random.randint(20, max_height)
        x = random.randint(0, SCREEN_WIDTH - width)
        y = random.randint(0, SCREEN_HEIGHT - height)
        obstacles.append(Obstacle(x, y, width, height))
    return obstacles


def respawn_food(food_cells, obstacles):
    if len(food_cells) < MIN_FOOD_CELLS:
        spawn_rate = 1.0
    else:
        relative_food_cells = (MAX_FOOD_CELLS - len(food_cells)) / (MAX_FOOD_CELLS - MIN_FOOD_CELLS)
        spawn_rate = FOOD_RESPAWN_RATE * relative_food_cells
    if len(food_cells) < MAX_FOOD_CELLS and random.random() < spawn_rate:
        mean_x = SCREEN_WIDTH / 2
        mean_y = SCREEN_HEIGHT / 2
        std_dev = min(SCREEN_WIDTH, SCREEN_HEIGHT) / 4
        while True:
            new_x = max(0, min(int(random.gauss(mean_x, std_dev)), SCREEN_WIDTH - CELL_SIZE))
            new_y = max(0, min(int(random.gauss(mean_y, std_dev)), SCREEN_HEIGHT - CELL_SIZE))
            new_x = (new_x // CELL_SIZE) * CELL_SIZE
            new_y = (new_y // CELL_SIZE) * CELL_SIZE
            if not any(obstacle.is_collision(new_x, new_y) for obstacle in obstacles):
                new_food = Food(new_x, new_y)
                food_cells.append(new_food)
                break


def draw_debug_view(screen, cell, center_x, center_y, font):
    """Draw debug information for a single cell."""
    # Energy bar (stamina)
    energy_ratio = cell.stamina / MAX_STAMINA
    energy_bar_width = CELL_SIZE * 3
    energy_bar_height = 3
    energy_bar_x = cell.x - energy_bar_width // 2 + CELL_SIZE // 2
    energy_bar_y = cell.y - 15  # Above the cell
    pygame.draw.rect(screen, WHITE, (energy_bar_x, energy_bar_y, energy_bar_width, energy_bar_height), 1)  # Border
    pygame.draw.rect(screen, YELLOW, (energy_bar_x, energy_bar_y, energy_bar_width * energy_ratio, energy_bar_height))  # Fill

    # Food bar (Hunger)
    food_ratio = cell.hunger / MAX_HUNGER
    food_bar_width = CELL_SIZE * 3
    food_bar_height = 3
    food_bar_x = cell.x - energy_bar_width // 2 + CELL_SIZE // 2
    food_bar_y = cell.y - 10  # Above the cell
    pygame.draw.rect(screen, WHITE, (food_bar_x, food_bar_y, food_bar_width, food_bar_height), 1)  # Border
    pygame.draw.rect(screen, GREEN, (food_bar_x, food_bar_y, food_bar_width * food_ratio, food_bar_height))  # Fill

    # Health bar
    health_ratio = cell.hp / MAX_HP
    health_bar_width = CELL_SIZE * 3
    health_bar_height = 3
    health_bar_x = cell.x - health_bar_width // 2 + CELL_SIZE // 2
    health_bar_y = energy_bar_y - 5  # Above the energy bar
    pygame.draw.rect(screen, WHITE, (health_bar_x, health_bar_y, health_bar_width, health_bar_height), 1)  # Border
    pygame.draw.rect(screen, RED, (health_bar_x, health_bar_y, health_bar_width * health_ratio, health_bar_height))  # Fill

    # Direction indicator
    if cell.direction_x != 0 or cell.direction_y != 0:
        dir_length = math.hypot(cell.direction_x, cell.direction_y)
        if dir_length != 0:
            dir_x_norm = cell.direction_x / dir_length
            dir_y_norm = cell.direction_y / dir_length

            # Set the length of the direction line
            dir_line_length = CELL_SIZE * 2

            # Calculate end point of the line
            end_x = cell.x + CELL_SIZE // 2 + dir_x_norm * dir_line_length
            end_y = cell.y + CELL_SIZE // 2 + dir_y_norm * dir_line_length

            pygame.draw.line(screen, GREEN, (cell.x + CELL_SIZE // 2, cell.y + CELL_SIZE // 2),
                             (end_x, end_y), 2)

    # Distance to center
    distance_to_center = math.hypot(cell.x - center_x, cell.y - center_y)
    distance_text = font.render(f"{int(distance_to_center)}", True, WHITE)
    text_x = cell.x - distance_text.get_width() // 2 + CELL_SIZE // 2
    text_y = cell.y + CELL_SIZE + 5  # Below the cell
    screen.blit(distance_text, (text_x, text_y))

    # Energy usage multiplier
    energy_multiplier = calculate_energy_multiplier(cell)  # Get the multiplier
    energy_text = font.render(f"×{energy_multiplier:.2f}", True, WHITE)
    text_x = cell.x - energy_text.get_width() // 2 + CELL_SIZE // 2
    text_y = cell.y + CELL_SIZE + 16  # Below the cell
    screen.blit(energy_text, (text_x, text_y))



def reset_simulation(num_cells, num_food, obstacles):
    """Reset simulation state with new cells and food."""
    cells = [
        Cell(
            random.randint(0, SCREEN_WIDTH // CELL_SIZE) * CELL_SIZE,
            random.randint(0, SCREEN_HEIGHT // CELL_SIZE) * CELL_SIZE
        )
        for _ in range(num_cells)
    ]
    food_cells = []
    while len(food_cells) < num_food:
        x = random.randint(0, SCREEN_WIDTH // CELL_SIZE) * CELL_SIZE
        y = random.randint(0, SCREEN_HEIGHT // CELL_SIZE) * CELL_SIZE
        if not any(obstacle.is_collision(x, y) for obstacle in obstacles):
            food_cells.append(Food(x, y))
    return cells, food_cells

def draw_stats_sidebar(screen, font, live_cells, food_cells, highest_generation, live_cells_history, food_cells_history, graph_surface_cells, graph_surface_food, max_ticks=0):
    """Draw a sidebar with statistics and two graphs."""
    sidebar_width = 300
    sidebar_x = SCREEN_WIDTH  # Sidebar starts where the main screen ends
    graph_height = 75
    graph_width = sidebar_width - 20  # Leave padding
    graph_x = sidebar_x + 10  # Padding from the edge
    graph_y_cells = SCREEN_HEIGHT - (graph_height * 2) - 30  # Position first graph
    graph_y_food = SCREEN_HEIGHT - graph_height - 20  # Position second graph

    # Ensure max_ticks is valid
    if max_ticks <= 0:
        max_ticks = min(len(live_cells_history), len(food_cells_history), 10000)  # Use available data or 100 points

    # Render stats text
    text_y = 20
    spacing = 40

    def draw_text(line, y):
        """Helper function to render text on the sidebar."""
        text_surface = font.render(line, True, WHITE)
        screen.blit(text_surface, (sidebar_x + 10, y))

    # Statistics
    draw_text(f"Cells: {len(live_cells)}", text_y)
    text_y += spacing
    draw_text(f"Food: {len(food_cells)}", text_y)
    text_y += spacing
    draw_text(f"Generation: {highest_generation}", text_y)
    text_y += spacing

    # Draw Live Cells Graph
    if live_cells_history:
        graph_surface_cells.fill(BLACK)
        max_value_cells = max(max(live_cells_history), 1)
        scaled_data_cells = [(value / max_value_cells) * graph_height for value in live_cells_history[-max_ticks:]]
        for i in range(1, len(scaled_data_cells)):
            x1 = (i - 1) * (graph_width / max_ticks)
            y1 = graph_height - scaled_data_cells[i - 1]
            x2 = i * (graph_width / max_ticks)
            y2 = graph_height - scaled_data_cells[i]
            pygame.draw.line(graph_surface_cells, GREEN, (x1, y1), (x2, y2), 2)
        screen.blit(graph_surface_cells, (graph_x, graph_y_cells))
        draw_text("Live Cells", graph_y_cells - 20)


    # Draw Food Cells Graph
    if food_cells_history:
        graph_surface_food.fill(BLACK)
        max_value_food = max(max(food_cells_history), 1)
        scaled_data_food = [(value / max_value_food) * graph_height for value in food_cells_history[-max_ticks:]]
        for i in range(1, len(scaled_data_food)):
            x1 = (i - 1) * (graph_width / max_ticks)
            y1 = graph_height - scaled_data_food[i - 1]
            x2 = i * (graph_width / max_ticks)
            y2 = graph_height - scaled_data_food[i]
            pygame.draw.line(graph_surface_food, BLUE, (x1, y1), (x2, y2), 2)
        screen.blit(graph_surface_food, (graph_x, graph_y_food))
        draw_text("Food Available", graph_y_food - 20)

    # Calculate additional stats if cells exist
    if live_cells:
        avg_hunger = sum(cell.hunger for cell in live_cells) / len(live_cells)
        avg_stamina = sum(cell.stamina for cell in live_cells) / len(live_cells)
        avg_age = sum(cell.age for cell in live_cells) / len(live_cells)
        draw_text(f"Avg Hunger: {avg_hunger:.1f}", text_y)
        text_y += spacing
        draw_text(f"Avg Stamina: {avg_stamina:.1f}", text_y)
        text_y += spacing
        draw_text(f"Avg Age: {avg_age:.1f}", text_y)



def calculate_energy_multiplier(cell):
    """Calculate the energy usage multiplier based on distance from the center."""
    center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    distance = math.hypot(cell.x - center_x, cell.y - center_y)

    # Normalize the distance to create a multiplier
    max_distance = math.hypot(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    multiplier = 1 + (distance / max_distance) * 2  # Scale multiplier (adjust factor as needed)

    return multiplier


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH + 300, SCREEN_HEIGHT)) # extend for sidebar
    pygame.display.set_caption("Pixel Life")

    graph_surface_cells = pygame.Surface((300, 75))
    graph_surface_cells.fill(BLACK)
    graph_surface_food = pygame.Surface((300, 75))
    graph_surface_food.fill(BLACK)

    # Generate obstacles before resetting
    obstacles = generate_random_obstacles(NUM_OBSTACLES, MAX_OBSTACLE_WIDTH, MAX_OBSTACLE_HEIGHT)

    # Call reset with obstacles
    cells, food_cells = reset_simulation(NUM_INITIAL_CELLS, NUM_INITIAL_FOOD, obstacles)
    spatial_grid = SpatialGrid(SCREEN_WIDTH, SCREEN_HEIGHT, GRID_CELL_SIZE)
    for cell in cells:
        spatial_grid.add(cell)

    def draw_obstacles(screen, obstacles):
        for obstacle in obstacles:
            pygame.draw.rect(screen, GRAY, (obstacle.x, obstacle.y, obstacle.width, obstacle.height))


    cells, food_cells = reset_simulation(NUM_INITIAL_CELLS, NUM_INITIAL_FOOD, obstacles)
    spatial_grid = SpatialGrid(SCREEN_WIDTH, SCREEN_HEIGHT, GRID_CELL_SIZE)
    for cell in cells:
        spatial_grid.add(cell)

    obstacles = generate_random_obstacles(NUM_OBSTACLES, MAX_OBSTACLE_WIDTH, MAX_OBSTACLE_HEIGHT)


    clock = pygame.time.Clock()
    running = True
    paused = False
    draw_mode = False
    debug_view = False  # Global debug view flag

    font = pygame.font.Font(None, 16)  # Initialize font
    sidebar_font = pygame.font.Font(None, 36)  # Initialize font

    while running:
        screen.fill(BLACK)
        # Declare globals at the beginning of the function if they are modified
        global FOOD_RESPAWN_RATE
        global MIN_FOOD_CELLS

        live_cells_count = len(cells)
        food_cells_count = len(food_cells)
        highest_generation = max((cell.generation for cell in cells), default=0)
        live_cells_history.append(live_cells_count)
        food_cells_history.append(food_cells_count)

        # Ensure synchronized updates for ticks and histories
        ticks.append(len(ticks) + 1)
        highest_generation_history.append(highest_generation)

        # Draw obstacles first
        #draw_obstacles(screen, obstacles)


        # Draw the sidebar with statistics
        draw_stats_sidebar(screen, sidebar_font, cells, food_cells, highest_generation, live_cells_history, food_cells_history, graph_surface_cells, graph_surface_food, max_ticks=0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    obstacles = generate_random_obstacles(NUM_OBSTACLES, MAX_OBSTACLE_WIDTH, MAX_OBSTACLE_HEIGHT)
                    cells, food_cells = reset_simulation(NUM_INITIAL_CELLS, NUM_INITIAL_FOOD, obstacles)
                    spatial_grid = SpatialGrid(SCREEN_WIDTH, SCREEN_HEIGHT, GRID_CELL_SIZE)
                    for cell in cells:
                        spatial_grid.add(cell)
                    print("Reset grid and obstacles.")
                elif event.key == pygame.K_p:
                    paused = not paused
                    print("Pause Toggled.")
                elif event.key == pygame.K_d:
                    draw_mode = not draw_mode
                    print("Toggled draw mode.")
                elif event.key == pygame.K_UP:
                    MIN_FOOD_CELLS += 1
                    print(f"Increased Minimum food cells to: {MIN_FOOD_CELLS}")
                elif event.key == pygame.K_DOWN:
                    MIN_FOOD_CELLS = max(0, MIN_FOOD_CELLS - 1)
                    print(f"Decreased Minimum food cells to: {MIN_FOOD_CELLS}")
                elif event.key == pygame.K_RIGHT:
                    FOOD_RESPAWN_RATE = min(FOOD_RESPAWN_RATE + 0.1, 10.0)
                    print(f"Increased food respawn rate: {FOOD_RESPAWN_RATE}")
                elif event.key == pygame.K_LEFT:
                    FOOD_RESPAWN_RATE = max(FOOD_RESPAWN_RATE - 0.1, 0.0)
                    print(f"Decreased food respawn rate: {FOOD_RESPAWN_RATE}")
                elif event.key == pygame.K_F1:
                    debug_view = not debug_view
                    print(f"Debug view {'enabled' if debug_view else 'disabled'}.")


            elif event.type == pygame.MOUSEBUTTONDOWN and draw_mode:
                x, y = pygame.mouse.get_pos()
                x = (x // CELL_SIZE) * CELL_SIZE
                y = (y // CELL_SIZE) * CELL_SIZE
                if event.button == 1:  # Left click
                    cell = Cell(x, y)
                    cells.append(cell)
                    spatial_grid.add(cell)
                    print("Spawned Cell")
                elif event.button == 3:  # Right click
                    food_cells.append(Food(x, y))
                    print("Spawned Food.")

        if not paused:
            new_cells = []
            for cell in cells:
                cell.move(food_cells, spatial_grid, obstacles)
                cell.update_status()
                for food in food_cells:
                    if cell.x == food.x and cell.y == food.y:
                        cell.eat(food, food_cells)
                for other in spatial_grid.get_nearby(cell.x, cell.y):
                    if cell != other and cell.is_adjacent(other):
                        if not cell.is_mating and not other.is_mating and cell.mating_cooldown == 0 and other.mating_cooldown == 0:
                            cell.start_mating(other)
                    if cell.is_mating and other.is_mating and cell.is_adjacent(other):
                        offspring = cell.mate(other, spatial_grid, obstacles)  # Pass obstacles here
                        new_cells.extend(offspring)
                if cell.hp <= 0:
                    spatial_grid.remove(cell)
                    cells.remove(cell)
                if cell.hp > 0:
                    if cell.is_mating:
                        color = HOT_PINK
                    elif cell.stamina == 0 and cell.hunger >= 10:
                        color = RED
                    elif cell.hunger > 90:
                        color = CYAN
                    elif cell.mating_cooldown >= 1:
                        color = PINK
                    elif cell.stamina <= 20:
                        color = YELLOW
                    elif cell.hunger >= 90 and cell.stamina >= 75:
                        color = BLUE
                    elif cell.stamina <= 15 and cell.hunger <= 30:
                        color = ORANGE
                    elif cell.age >= 400:
                        color = GRAY
                    else:
                        color = WHITE
                    # Draw the cell
                    pygame.draw.rect(screen, color, (cell.x, cell.y, CELL_SIZE, CELL_SIZE))

                    # Draw debug view for the current cell
                    if debug_view:
                        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
                        draw_debug_view(screen, cell, center_x, center_y, font)
                        #print(f"Debug view drawn for cell at ({cell.x}, {cell.y})") # Spams console

            cells.extend(new_cells)
            respawn_food(food_cells, obstacles)

            for food in food_cells:
                if food.x != -1 and food.y != -1:
                    pygame.draw.rect(screen, GREEN, (food.x, food.y, CELL_SIZE, CELL_SIZE))

            pygame.display.flip()
            clock.tick(TICK_RATE)

    pygame.quit()

if __name__ == "__main__":
    main()
