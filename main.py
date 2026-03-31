import pygame
import sys
import math
import random
import colorsys

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("BallWithinBound")

# Colors
BLACK = (0, 0, 0)
DARK_GRAY = (50, 50, 50)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BUTTON_COLOR = (100, 100, 100)
BUTTON_HOVER = (120, 120, 120)

# Physics parameters
acceleration = 1.0  # Default acceleration
collision_coefficient = 1.0  # Default collision coefficient (elastic)

# Trail parameters
trail_enabled = False  # Default trail state
trail_duration = 5.0  # Default trail duration in seconds
MAX_TRAIL_POINTS = 1000  # Maximum number of trail points to store

# Random seed for reproducible initial conditions
random_seed = 42  # Change this value to get different initial states

# Pentagon parameters
pentagon_radius = 200
pentagon_center = (WIDTH // 2, HEIGHT // 2)
rotation_speed = 30  # degrees per second
rotation_angle = 0
num_edges = 5  # Starting with pentagon (5 edges)

# Ball parameters
ball_radius = 8
ball_pos = [pentagon_center[0], pentagon_center[1]]  # Will be initialized with random values
ball_vel = [150.0, 0.0]  # Will be initialized with random values

# Slider parameters
slider_width = 200
slider_height = 20
slider_x = 10
slider_margin = 40

# Font
try:
    font = pygame.font.SysFont('Arial', 20)
    small_font = pygame.font.SysFont('Arial', 14)
except:
    font = pygame.font.Font(None, 20)
    small_font = pygame.font.Font(None, 14)

# Clock for controlling frame rate
clock = pygame.time.Clock()
FPS = 60

def get_polygon_vertices(center, radius, angle, num_sides):
    """Calculate the vertices of a regular polygon"""
    vertices = []
    # Calculate angle between vertices
    angle_step = 360 / num_sides
    for i in range(num_sides):
        vertex_angle = math.radians(angle + i * angle_step)
        x = center[0] + radius * math.cos(vertex_angle)
        y = center[1] + radius * math.sin(vertex_angle)
        vertices.append((x, y))
    return vertices


def get_inner_polygon_vertices(center, outer_radius, inner_radius, angle, num_sides):
    """Calculate vertices of inner polygon for ball constraint"""
    vertices = []
    # Calculate angle between vertices
    angle_step = 360 / num_sides
    for i in range(num_sides):
        vertex_angle = math.radians(angle + i * angle_step)
        x = center[0] + inner_radius * math.cos(vertex_angle)
        y = center[1] + inner_radius * math.sin(vertex_angle)
        vertices.append((x, y))
    return vertices


def constrain_ball_to_polygon(ball_pos, center, outer_radius, ball_radius, angle, num_sides):
    """Constrain ball position to stay within inner polygon"""
    inner_radius = outer_radius - ball_radius
    
    # Get inner polygon vertices
    inner_vertices = get_inner_polygon_vertices(center, outer_radius, inner_radius, angle, num_sides)
    
    # Check if ball is outside inner polygon
    # Using point-in-polygon test with barycentric coordinates
    px, py = ball_pos
    n = len(inner_vertices)
    inside = False
    
    # Ray casting algorithm to check if point is inside polygon
    xinters = 0
    p1x, p1y = inner_vertices[0]
    for i in range(n+1):
        p2x, p2y = inner_vertices[i % n]
        if py > min(p1y, p2y):
            if py <= max(p1y, p2y):
                if px <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or px <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    # If ball is outside, find closest edge and push it back inside
    if not inside:
        min_distance = float('inf')
        closest_point = None
        
        for i in range(n):
            start = inner_vertices[i]
            end = inner_vertices[(i + 1) % n]
            
            # Calculate distance to edge
            distance, projection = distance_point_to_line(ball_pos, start, end)
            if distance < min_distance:
                min_distance = distance
                closest_point = projection
                
                # Calculate edge vector for normal
                edge_vec = (end[0] - start[0], end[1] - start[1])
                normal = (-edge_vec[1], edge_vec[0])
                
                # Normalize normal
                length = math.sqrt(normal[0]**2 + normal[1]**2)
                if length > 0:
                    normal = (normal[0]/length, normal[1]/length)
        
        # Push ball back inside along normal direction
        if closest_point and normal:
            # Move ball to just inside the boundary
            ball_pos[0] = closest_point[0] - normal[0] * 0.1
            ball_pos[1] = closest_point[1] - normal[1] * 0.1
            
    return ball_pos

def distance_point_to_line(point, line_start, line_end):
    """Calculate the distance from a point to a line segment"""
    x, y = point
    x1, y1 = line_start
    x2, y2 = line_end
    
    # Vector from line_start to line_end
    line_vec = (x2 - x1, y2 - y1)
    # Vector from line_start to point
    point_vec = (x - x1, y - y1)
    
    # Length of line segment squared
    line_length_sq = line_vec[0]**2 + line_vec[1]**2
    
    # Project point_vec onto line_vec
    if line_length_sq == 0:
        return math.sqrt(point_vec[0]**2 + point_vec[1]**2)
    
    t = max(0, min(1, (point_vec[0] * line_vec[0] + point_vec[1] * line_vec[1]) / line_length_sq))
    
    # Calculate projection point
    projection = (x1 + t * line_vec[0], y1 + t * line_vec[1])
    
    # Distance from point to projection
    dx = x - projection[0]
    dy = y - projection[1]
    return math.sqrt(dx**2 + dy**2), projection

def check_collision(ball_pos, ball_radius, vertices):
    """Check if ball collides with any polygon edge or vertex"""
    num_sides = len(vertices)
    
    # First check for edge collisions
    for i in range(num_sides):
        start = vertices[i]
        end = vertices[(i + 1) % num_sides]
        
        distance, closest_point = distance_point_to_line(ball_pos, start, end)
        
        if distance <= ball_radius:
            # Calculate normal vector (perpendicular to the edge)
            edge_vec = (end[0] - start[0], end[1] - start[1])
            normal = (-edge_vec[1], edge_vec[0])
            
            # Normalize normal vector
            normal_length = math.sqrt(normal[0]**2 + normal[1]**2)
            if normal_length > 0:
                normal = (normal[0] / normal_length, normal[1] / normal_length)
            
            return True, normal, closest_point
    
    # Then check for vertex collisions
    for vertex in vertices:
        distance = math.sqrt((ball_pos[0] - vertex[0])**2 + (ball_pos[1] - vertex[1])**2)
        if distance <= ball_radius:
            # Calculate normal vector from vertex to ball (outward from polygon)
            normal = (ball_pos[0] - vertex[0], ball_pos[1] - vertex[1])
            
            # Normalize normal vector
            normal_length = math.sqrt(normal[0]**2 + normal[1]**2)
            if normal_length > 0:
                normal = (normal[0] / normal_length, normal[1] / normal_length)
            
            return True, normal, vertex
    
    return False, None, None

def handle_collision(ball_vel, normal, collision_coefficient):
    """Handle collision response"""
    # Dot product of velocity and normal
    dot_product = ball_vel[0] * normal[0] + ball_vel[1] * normal[1]
    
    # Apply collision response
    ball_vel[0] = ball_vel[0] - 2 * dot_product * normal[0] * collision_coefficient
    ball_vel[1] = ball_vel[1] - 2 * dot_product * normal[1] * collision_coefficient

def create_slider(x, y, width, height, value, min_val, max_val, dragging=False):
    """Create a slider control"""
    # Draw slider track
    pygame.draw.rect(screen, DARK_GRAY, (x, y, width, height))
    pygame.draw.rect(screen, WHITE, (x, y, width, height), 1)
    
    # Calculate slider position
    slider_pos = x + (value - min_val) / (max_val - min_val) * width
    
    # Draw slider handle
    handle_color = BUTTON_HOVER if dragging else BUTTON_COLOR
    pygame.draw.rect(screen, handle_color, (slider_pos - 5, y - 5, 10, height + 10))
    pygame.draw.rect(screen, WHITE, (slider_pos - 5, y - 5, 10, height + 10), 1)


class Particle:
    def __init__(self, x, y, velocity, color, max_distance):
        self.x = x
        self.y = y
        self.velocity = velocity  # (vx, vy)
        self.color = color
        self.max_distance = max_distance
        self.initial_x = x
        self.initial_y = y
        self.alive = True

    def update(self):
        # Update position
        self.x += self.velocity[0] / FPS
        self.y += self.velocity[1] / FPS
        
        # Calculate distance from initial position
        distance = math.sqrt((self.x - self.initial_x)**2 + (self.y - self.initial_y)**2)
        
        # Check if particle is still alive
        if distance >= self.max_distance:
            self.alive = False
        return self.alive

    def draw(self, surface):
        # Calculate distance from initial position
        distance = math.sqrt((self.x - self.initial_x)**2 + (self.y - self.initial_y)**2)
        
        # Calculate alpha based on distance (linear fade out)
        alpha = 255 * (1 - distance / self.max_distance)
        alpha = max(0, min(255, int(alpha)))  # Clamp between 0 and 255
        
        # Create a temporary surface with per-pixel alpha
        temp_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
        
        # Create color with alpha
        color_with_alpha = (*self.color, alpha)
        
        # Draw particle on temporary surface
        pygame.draw.circle(temp_surface, color_with_alpha, (2, 2), 2)
        
        # Blit the temporary surface onto the main surface
        surface.blit(temp_surface, (int(self.x) - 2, int(self.y) - 2))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def add_explosion(self, x, y, num_particles=20, max_distance=None):
        if max_distance is None:
            max_distance = 4.5 * ball_radius * 2  # 4.5 times ball diameter (1.5x the previous range)
            
        # Generate a random color for all particles in this explosion
        hue = random.random()  # Random hue between 0 and 1
        rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)  # Full saturation and brightness
        color = (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
        
        # Create particles moving in random directions
        for _ in range(num_particles):
            # Random angle
            angle = random.uniform(0, 2 * math.pi)
            
            # Random speed (adjust as needed)
            speed = random.uniform(50, 200)
            
            # Calculate velocity components
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            
            # Create particle
            particle = Particle(x, y, (vx, vy), color, max_distance)
            self.particles.append(particle)

    def update(self):
        # Update all particles and remove dead ones
        self.particles = [p for p in self.particles if p.update()]

    def draw(self, surface):
        # Draw all particles
        for particle in self.particles:
            particle.draw(surface)

def initialize_ball_state(seed_value):
    """Initialize ball position and velocity based on random seed"""
    random.seed(seed_value)
    
    # Generate random position near pentagon center
    # Position within 20 pixels of the center
    offset_x = random.uniform(-20, 20)
    offset_y = random.uniform(-20, 20)
    ball_pos[0] = pentagon_center[0] + offset_x
    ball_pos[1] = pentagon_center[1] + offset_y
    
    # Generate random velocity with magnitude between 50 and 200
    speed = random.uniform(50, 200)
    angle = random.uniform(0, 2 * math.pi)  # Random direction
    ball_vel[0] = speed * math.cos(angle)
    ball_vel[1] = speed * math.sin(angle)

def main():
    global rotation_angle, ball_pos, ball_vel, acceleration, collision_coefficient, random_seed, num_edges, trail_enabled, trail_duration
    
    # Initialize ball state with random seed
    initialize_ball_state(random_seed)
    
    # Initialize trail points list
    trail_points = []
    
    # Initialize particle system
    particle_system = ParticleSystem()
    
    # Slider dragging states
    dragging_acceleration = False
    dragging_collision = False
    dragging_trail_duration = False
    
    # Toggle button state
    add_edge_enabled = False
    button_rect = pygame.Rect(WIDTH - 60, 10, 50, 30)
    trail_button_rect = pygame.Rect(WIDTH - 140, 10, 70, 30)  # Trail button to the left of EDGE button
    
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                
                # Check if clicking on acceleration slider
                acc_slider_y = 20
                if (slider_x <= mouse_x <= slider_x + slider_width and 
                    acc_slider_y - 5 <= mouse_y <= acc_slider_y + slider_height + 5):
                    dragging_acceleration = True
                
                # Check if clicking on collision coefficient slider
                col_slider_y = 20 + slider_margin
                if (slider_x <= mouse_x <= slider_x + slider_width and 
                    col_slider_y - 5 <= mouse_y <= col_slider_y + slider_height + 5):
                    dragging_collision = True
                    
                # Check if clicking on trail duration slider
                trail_slider_y = 20 + 2 * slider_margin
                if (slider_x <= mouse_x <= slider_x + slider_width and 
                    trail_slider_y - 5 <= mouse_y <= trail_slider_y + slider_height + 5):
                    dragging_trail_duration = True
                    
                # Check if clicking on toggle button
                if button_rect.collidepoint(mouse_x, mouse_y):
                    add_edge_enabled = not add_edge_enabled
                    
                # Check if clicking on trail toggle button
                if trail_button_rect.collidepoint(mouse_x, mouse_y):
                    trail_enabled = not trail_enabled
                
            elif event.type == pygame.MOUSEBUTTONUP:
                dragging_acceleration = False
                dragging_collision = False
                dragging_trail_duration = False
                
            elif event.type == pygame.MOUSEMOTION:
                if dragging_acceleration:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    # Calculate new acceleration value
                    relative_x = max(0, min(slider_width, mouse_x - slider_x))
                    acceleration = 0.1 + (relative_x / slider_width) * 9.9  # Range: 0.1 to 10.0
                    
                elif dragging_collision:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    # Calculate new collision coefficient value
                    relative_x = max(0, min(slider_width, mouse_x - slider_x))
                    collision_coefficient = relative_x / slider_width  # Range: 0.0 to 1.0
                    
                elif dragging_trail_duration:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    # Calculate new trail duration value (0.5 to 10.0 seconds)
                    relative_x = max(0, min(slider_width, mouse_x - slider_x))
                    trail_duration = 0.5 + (relative_x / slider_width) * 9.5  # Range: 0.5 to 10.0
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:  # Press 'R' to reinitialize with same seed
                    initialize_ball_state(random_seed)
                elif event.key == pygame.K_n:  # Press 'N' to change seed and reinitialize
                    random_seed = random.randint(1, 1000)
                    initialize_ball_state(random_seed)
        
        # Update rotation angle
        rotation_angle += rotation_speed / FPS
        if rotation_angle >= 360:
            rotation_angle -= 360
        
        # Get current polygon vertices
        vertices = get_polygon_vertices(pentagon_center, pentagon_radius, rotation_angle, num_edges)
        
        # Update ball physics
        ball_vel[1] += acceleration  # Apply acceleration (gravity)
        ball_pos[0] += ball_vel[0] / FPS
        ball_pos[1] += ball_vel[1] / FPS
        
        # Constrain ball to stay within inner polygon
        ball_pos = constrain_ball_to_polygon(ball_pos, pentagon_center, pentagon_radius, ball_radius, rotation_angle, num_edges)
        
        # Check for collisions (for visual effect and sound if needed)
        collision, normal, closest_point = check_collision(ball_pos, ball_radius, vertices)
        if collision:
            # Handle collision response
            handle_collision(ball_vel, normal, collision_coefficient)
            
            # Create particle explosion at collision point
            if closest_point:
                particle_system.add_explosion(closest_point[0], closest_point[1])
            
            # Increase edges on collision if toggle is enabled
            if add_edge_enabled:
                num_edges += 1
                
        # Update particle system
        particle_system.update()
                
        # Manage trail points
        if trail_enabled:
            # Add current ball position to trail
            current_time = pygame.time.get_ticks() / 1000.0  # Convert to seconds
            trail_points.append((ball_pos[0], ball_pos[1], current_time))
            
            # Remove old trail points
            # Keep only points within the trail duration
            while trail_points and (current_time - trail_points[0][2]) > trail_duration:
                trail_points.pop(0)
                
            # Limit trail points to MAX_TRAIL_POINTS
            if len(trail_points) > MAX_TRAIL_POINTS:
                trail_points = trail_points[-MAX_TRAIL_POINTS:]
                
        # Clear screen
        screen.fill(BLACK)
        
        # Draw pentagon
        pygame.draw.polygon(screen, DARK_GRAY, vertices)
        pygame.draw.polygon(screen, WHITE, vertices, 2)
        
        # Draw trail if enabled (draw after polygon so it's on top)
        if trail_enabled and len(trail_points) > 1:
            # Draw trail with 12 gradient layers from purple to dark gray
            layer_colors = [
                (117, 41, 232),
                (111, 42, 216),
                (105, 43, 199),
                (99, 44, 183),
                (93, 45, 166),
                (87, 46, 150),
                (81, 46, 133),
                (75, 47, 117),
                (69, 48, 100),
                (63, 49, 84),
                (57, 50, 67),
                (51, 51, 51)      # Dark gray (background color)
            ]
            
            # Duration factors from 0.1 to 1.0 (increasing)
            layer_durations = [i / 11.0 for i in range(1, 13)]  # 0.09, 0.18, ..., 1.0
            
            # Alpha values from 255 to 20 (decreasing)
            layer_alphas = [255 - i * 20 for i in range(12)]  # 255, 235, ..., 35
            layer_alphas[-1] = 20  # Last layer more transparent
            
            line_width = int(ball_radius * 0.8)  # 0.8 times ball diameter
            
            # Draw each layer independently, from longest duration to shortest duration
            # This ensures shorter duration (brighter) trails are drawn on top
            for layer in reversed(range(12)):  # Draw from layer 11 to layer 0
                layer_duration = trail_duration * layer_durations[layer]
                base_color = layer_colors[layer]
                max_alpha = layer_alphas[layer]
                
                for i in range(1, len(trail_points)):
                    # Calculate alpha based on age of the point for this layer
                    age = current_time - trail_points[i][2]
                    # Alpha goes from max_alpha (newest) to 0 (oldest) within layer duration
                    if age <= layer_duration:
                        alpha = int(max_alpha * (1 - age / layer_duration))
                        
                        if alpha > 0:
                            # Draw line between consecutive points
                            start_pos = (int(trail_points[i-1][0]), int(trail_points[i-1][1]))
                            end_pos = (int(trail_points[i][0]), int(trail_points[i][1]))
                            # Draw with anti-aliasing if possible
                            pygame.draw.line(screen, base_color, start_pos, end_pos, line_width)
                            
        # Draw particles (before ball so they appear behind it)
        particle_system.draw(screen)
        
        # Draw pentagon center point
        pygame.draw.circle(screen, WHITE, pentagon_center, 3)
        
        # Draw ball
        pygame.draw.circle(screen, RED, (int(ball_pos[0]), int(ball_pos[1])), ball_radius)
        
        # Draw toggle buttons
        # Draw EDGE button
        button_color = BUTTON_HOVER if button_rect.collidepoint(pygame.mouse.get_pos()) else BUTTON_COLOR
        pygame.draw.rect(screen, button_color, button_rect)
        pygame.draw.rect(screen, WHITE, button_rect, 2)
        
        # Draw button text
        button_text = font.render("EDGE", True, WHITE)
        text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, text_rect)
        
        # Draw toggle state text
        state_text = small_font.render(f"Add Edge {'ON' if add_edge_enabled else 'OFF'}", True, WHITE)
        screen.blit(state_text, (button_rect.x - 10, button_rect.y + 35))
        
        # Draw Trail button
        trail_button_color = BUTTON_HOVER if trail_button_rect.collidepoint(pygame.mouse.get_pos()) else BUTTON_COLOR
        pygame.draw.rect(screen, trail_button_color, trail_button_rect)
        pygame.draw.rect(screen, WHITE, trail_button_rect, 2)
        
        # Draw trail button text
        trail_button_text = font.render("TRAIL", True, WHITE)
        trail_text_rect = trail_button_text.get_rect(center=trail_button_rect.center)
        screen.blit(trail_button_text, trail_text_rect)
        
        # Draw trail toggle state text
        trail_state_text = small_font.render(f"Trail {'ON' if trail_enabled else 'OFF'}", True, WHITE)
        screen.blit(trail_state_text, (trail_button_rect.x - 10, trail_button_rect.y + 35))
        
        # Draw UI sliders and text
        acc_slider_y = 20
        col_slider_y = 20 + slider_margin
        trail_slider_y = 20 + 2 * slider_margin
        
        # Acceleration slider
        create_slider(slider_x, acc_slider_y, slider_width, slider_height, 
                      acceleration, 0.1, 10.0, dragging_acceleration)
        acc_label = font.render("Acceleration (a):", True, WHITE)
        acc_value = font.render(f"{acceleration:.1f}", True, WHITE)
        screen.blit(acc_label, (slider_x + slider_width + 10, acc_slider_y))
        screen.blit(acc_value, (slider_x + slider_width + 150, acc_slider_y))
        
        # Collision coefficient slider
        create_slider(slider_x, col_slider_y, slider_width, slider_height, 
                      collision_coefficient, 0.0, 1.0, dragging_collision)
        col_label = font.render("Collision (e):", True, WHITE)
        col_value = font.render(f"{collision_coefficient:.2f}", True, WHITE)
        screen.blit(col_label, (slider_x + slider_width + 10, col_slider_y))
        screen.blit(col_value, (slider_x + slider_width + 150, col_slider_y))
        
        # Trail duration slider
        create_slider(slider_x, trail_slider_y, slider_width, slider_height, 
                      trail_duration, 0.5, 10.0, dragging_trail_duration)
        trail_label = font.render("Trail Duration:", True, WHITE)
        trail_value = font.render(f"{trail_duration:.1f}s", True, WHITE)
        screen.blit(trail_label, (slider_x + slider_width + 10, trail_slider_y))
        screen.blit(trail_value, (slider_x + slider_width + 150, trail_slider_y))
        
        # Update display
        pygame.display.flip()
        
        # Control frame rate
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()