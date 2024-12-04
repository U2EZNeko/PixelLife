# cell_simulation.py

import pygame
import random
import math
import matplotlib.pyplot as plt
import matplotlib
plt.rcParams['figure.raise_window'] = False

# Constants
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
CELL_SIZE = 5
GRID_CELL_SIZE = CELL_SIZE * 3
TICK_RATE = 30

# Game Variables
NUM_INITIAL_CELLS = 20
NUM_INITIAL_FOOD = 100
FOOD_RESPAWN_RATE = 0.2
STAMINA_PER_STEP = 0.5
FOOD_GAINED_FROM_FOOD_CELLS = 35
STAMINA_GAINED_FROM_FOOD_CELLS = 25
IDLE_STAMINA_GAIN = 0.5
IDLE_HUNGER_CONSUMPTION = 0.1

# Graph data
live_cells_history = []
food_cells_history = []
highest_generation_history = []
ticks = []

# Mating Data
MATING_STAMINA_COST = 90
MATING_HUNGER_COST = 80
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
MAX_AGE = 700
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

    def move_towards(self, target_x, target_y, spatial_grid):
        if self.stamina > 0:
            self.stamina -= STAMINA_PER_STEP
            direction_x = target_x - self.x
            direction_y = target_y - self.y
            distance_to_target = (direction_x ** 2 + direction_y ** 2) ** 0.5
            step_size = CELL_SIZE * (self.speed if self.speed > 0 else 1)
            if distance_to_target < step_size:
                step_size = distance_to_target
            if distance_to_target > 0:
                direction_x /= distance_to_target
                direction_y /= distance_to_target
            old_x, old_y = self.x, self.y
            new_x = self.x + direction_x * step_size
            new_y = self.y + direction_y * step_size
            new_x = max(min(new_x, SCREEN_WIDTH - CELL_SIZE), 0)
            new_y = max(min(new_y, SCREEN_HEIGHT - CELL_SIZE), 0)
            if not self.is_collision(new_x, new_y, spatial_grid):
                self.x, self.y = new_x, new_y
                spatial_grid.move(self, old_x, old_y)
        else:
            self.stamina = min(self.stamina + IDLE_STAMINA_GAIN, CELL_INITIAL_STAMINA)
        self.hunger += IDLE_HUNGER_CONSUMPTION

    def move(self, food_cells, spatial_grid):
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
                    self.move_towards(nearest_food.x, nearest_food.y, spatial_grid)
            elif self.hunger >= 90 and self.hp >= 90 and self.mating_cooldown == 0:
                nearest_mate = self.find_nearest_mate(spatial_grid.get_nearby(self.x, self.y))
                if nearest_mate:
                    self.move_towards(nearest_mate.x, nearest_mate.y, spatial_grid)
            else:
                if random.random() < 0.5:
                    return
                else:
                    self.move_randomly(spatial_grid)
            self.stamina -= STAMINA_PER_STEP
        else:
            self.stamina = min(self.stamina + IDLE_STAMINA_GAIN, MAX_STAMINA)

    def move_randomly(self, spatial_grid):
        directions = ['up', 'down', 'left', 'right']
        random.shuffle(directions)
        for direction in directions:
            new_x, new_y = self.x, self.y
            step_size = CELL_SIZE * (self.speed if self.speed > 0 else 1)
            if direction == 'up' and self.y > 0:
                new_y -= step_size
            elif direction == 'down' and self.y < SCREEN_HEIGHT - CELL_SIZE:
                new_y += step_size
            elif direction == 'left' and self.x > 0:
                new_x -= step_size
            elif direction == 'right' and self.x < SCREEN_WIDTH - CELL_SIZE:
                new_x += step_size
            if self.is_within_bounds(new_x, new_y) and not self.is_collision(new_x, new_y, spatial_grid):
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
        #print("Cell looking for mate.")
        nearest_mate = None
        min_distance = float('inf')
        for cell in cells:
            if cell != self and cell.hunger == CELL_INITIAL_HUNGER and cell.hp == CELL_INITIAL_HP and cell.mating_cooldown == 0 and not cell.is_mating:
                distance = math.hypot(self.x - cell.x, self.y - cell.y)
                if distance < min_distance:
                    min_distance = distance
                    nearest_mate = cell
                    print("Cell found a mate.")
        return nearest_mate

    def start_mating(self, other):
        print("Cell is Mating.")
        self.is_mating = True
        self.mating_timer = MATING_DURATION
        other.is_mating = True
        other.mating_timer = MATING_DURATION

    def mate(self, other, spatial_grid):
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
                if self.is_within_bounds(new_x, new_y) and not self.is_collision(new_x, new_y, spatial_grid):
                    new_cell = Cell(new_x, new_y, self.generation + 1)
                    new_cell.mating_cooldown = NEWBORN_MATING_COOLDOWN
                    new_cell.speed = (self.speed + other.speed) // 2
                    new_cell.max_hp = (self.max_hp + other.max_hp) // 2
                    new_cell.max_stamina = (self.max_stamina + other.max_stamina) // 2
                    new_cell.max_hunger = (self.max_hunger + other.max_hunger) // 2
                    offspring.append(new_cell)
                    spatial_grid.add(new_cell)
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

    def is_collision(self, x, y, spatial_grid):
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

def respawn_food(food_cells):
    if len(food_cells) < MIN_FOOD_CELLS:
        spawn_rate = 1.0
    else:
        relative_food_cells = (MAX_FOOD_CELLS - len(food_cells)) / (MAX_FOOD_CELLS - MIN_FOOD_CELLS)
        spawn_rate = FOOD_RESPAWN_RATE * relative_food_cells
    if len(food_cells) < MAX_FOOD_CELLS and random.random() < spawn_rate:
        mean_x = SCREEN_WIDTH / 2
        mean_y = SCREEN_HEIGHT / 2
        std_dev = min(SCREEN_WIDTH, SCREEN_HEIGHT) / 4
        new_x = max(0, min(int(random.gauss(mean_x, std_dev)), SCREEN_WIDTH - CELL_SIZE))
        new_y = max(0, min(int(random.gauss(mean_y, std_dev)), SCREEN_HEIGHT - CELL_SIZE))
        new_x = (new_x // CELL_SIZE) * CELL_SIZE
        new_y = (new_y // CELL_SIZE) * CELL_SIZE
        new_food = Food(new_x, new_y)
        food_cells.append(new_food)
        #print("Spawned a food cell.")

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Pixel Life")
    matplotlib.rcParams['figure.raise_window'] = False

    def reset():
        return [Cell(random.randint(0, SCREEN_WIDTH // CELL_SIZE) * CELL_SIZE,
                  random.randint(0, SCREEN_HEIGHT // CELL_SIZE) * CELL_SIZE) for _ in range(NUM_INITIAL_CELLS)], \
               [Food(random.randint(0, SCREEN_WIDTH // CELL_SIZE) * CELL_SIZE,
                     random.randint(0, SCREEN_HEIGHT // CELL_SIZE) * CELL_SIZE) for _ in range(NUM_INITIAL_FOOD)]

    cells, food_cells = reset()
    spatial_grid = SpatialGrid(SCREEN_WIDTH, SCREEN_HEIGHT, GRID_CELL_SIZE)
    for cell in cells:
        spatial_grid.add(cell)

    clock = pygame.time.Clock()
    running = True
    paused = False
    draw_mode = False

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))

    while running:
        screen.fill(BLACK)
        live_cells_count = len(cells)
        food_cells_count = len(food_cells)
        highest_generation = max((cell.generation for cell in cells), default=0)
        live_cells_history.append(live_cells_count)
        food_cells_history.append(food_cells_count)
        highest_generation_history.append(highest_generation)
        ticks.append(len(ticks) + 1)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    cells, food_cells = reset()
                    spatial_grid = SpatialGrid(SCREEN_WIDTH, SCREEN_HEIGHT, GRID_CELL_SIZE)
                    for cell in cells:
                        spatial_grid.add(cell)
                    print("Reset grid.")
                elif event.key == pygame.K_p:
                    paused = not paused
                    print("Pause Toggled.")
                elif event.key == pygame.K_d:
                    draw_mode = not draw_mode
                    print("Toggled draw mode.")
                elif event.key == pygame.K_UP:
                    global MIN_FOOD_CELLS
                    MIN_FOOD_CELLS += 1
                    print("Increased Minimum food cells to: " +str(MIN_FOOD_CELLS))
                elif event.key == pygame.K_DOWN:
                    MIN_FOOD_CELLS = max(0, MIN_FOOD_CELLS - 1)
                    print("Decreased Minimum food cells to: " +str(MIN_FOOD_CELLS))
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
                cell.move(food_cells, spatial_grid)
                cell.update_status()
                for food in food_cells:
                    if cell.x == food.x and cell.y == food.y:
                        cell.eat(food, food_cells)
                for other in spatial_grid.get_nearby(cell.x, cell.y):
                    if cell != other and cell.is_adjacent(other):
                        if not cell.is_mating and not other.is_mating and cell.mating_cooldown == 0 and other.mating_cooldown == 0:
                            cell.start_mating(other)
                    if cell.is_mating and other.is_mating and cell.is_adjacent(other):
                        offspring = cell.mate(other, spatial_grid)
                        new_cells.extend(offspring)
                if cell.hp <= 0:
                    spatial_grid.remove(cell)
                    cells.remove(cell)
                if cell.hp > 0:
                    if cell.is_mating:
                        color = HOT_PINK
                    elif cell.stamina == 0 and cell.hunger >= 10:
                        color = RED
                    elif cell.hunger > 60:
                        color = CYAN
                    elif cell.mating_cooldown >= 1:
                        color = PINK
                    elif cell.hunger >= 90 and cell.stamina >= 75:
                        color = BLUE
                    elif cell.stamina <= 15 and cell.hunger <= 30:
                        color = ORANGE
                    elif cell.age >= 400:
                        color = GRAY
                    else:
                        color = WHITE
                    pygame.draw.rect(screen, color, (cell.x, cell.y, CELL_SIZE, CELL_SIZE))

            cells.extend(new_cells)
            respawn_food(food_cells)

            for food in food_cells:
                if food.x != -1 and food.y != -1:
                    pygame.draw.rect(screen, GREEN, (food.x, food.y, CELL_SIZE, CELL_SIZE))

            pygame.display.flip()
            clock.tick(TICK_RATE)

            ax1.clear()
            ax1.plot(ticks, live_cells_history, label='Live Cells', color='blue')
            ax1.plot(ticks, food_cells_history, label='Food Cells', color='green')
            ax1.set_xlabel('Ticks')
            ax1.set_ylabel('Count')
            ax1.set_title('Live Cells and Food Cells Over Time')
            ax1.legend()

            ax2.clear()
            ax2.plot(ticks, highest_generation_history, label='Highest Generation', color='red')
            ax2.set_xlabel('Ticks')
            ax2.set_ylabel('Generation')
            ax2.set_title('Highest Generation Over Time')
            ax2.legend()

            plt.pause(0.001)

    pygame.quit()
    plt.show()

if __name__ == "__main__":
    main()
