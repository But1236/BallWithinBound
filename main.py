import pygame
import sys
import math
import random
import colorsys
from pygame import gfxdraw
import numpy as np
try:
    from drum_detection import DrumDetector
    DRUM_DETECTION_AVAILABLE = True
except ImportError:
    DRUM_DETECTION_AVAILABLE = False
    print("Drum detection module not available. Using simulated beats.")

# Enable high DPI awareness for better display quality
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # For Windows
except:
    pass

# Initialize pygame
pygame.init()
pygame.mixer.init()

# Screen dimensions - Increased to 1.5 times original size
WIDTH, HEIGHT = 1800, 1350
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("BallWithinBound")

# Colors
BLACK = (0, 0, 0)
DARK_GRAY = (50, 50, 50)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BUTTON_COLOR = (100, 100, 100)
BUTTON_HOVER = (120, 120, 120)

# Neon colors for polygon edges (all yellow now)
NEON_COLORS = [
    (255, 255, 0),    # Yellow
    (255, 255, 0),    # Yellow
    (255, 255, 0),    # Yellow
    (255, 255, 0),    # Yellow
    (255, 255, 0),    # Yellow
    (255, 255, 0),    # Yellow
    (255, 255, 0),    # Yellow
    (255, 255, 0),    # Yellow
    (255, 255, 0),    # Yellow
    (255, 255, 0)     # Yellow
]

# Physics parameters
acceleration = 9.8  # Default acceleration (Earth's gravity)
collision_coefficient = 1.0  # Default collision coefficient (elastic)

# Music parameters
music_enabled = False
music_playing = False
music_channel = None  # Channel for playing music

# Beat detection parameters
last_volume = 0
volume_threshold = 0.1  # Threshold for detecting volume peaks
beat_detected = False
beat_cooldown = 0  # Cooldown timer to prevent multiple beats from triggering too quickly
last_beat_time = 0  # Time of last beat
beat_interval = 0  # Interval between beats in seconds

# Drum detection
drum_detector = None  # Will be initialized when music is enabled
prev_audio_frame = None  # Store previous audio frame for spectral flux calculation

# Music text animation parameters
music_text_animation_time = 0  # Time elapsed since music was enabled
music_text_animation_duration = 2.0  # Duration of the animation in seconds

# Trail parameters
trail_enabled = False  # Default trail state
trail_duration = 1.5  # Default trail duration in seconds
MAX_TRAIL_POINTS = 1000  # Maximum number of trail points to store

# Random seed for reproducible initial conditions
random_seed = 42  # Change this value to get different initial states

# Pentagon parameters - Scaled up for better visibility
pentagon_radius = 450
pentagon_center = (WIDTH // 2, HEIGHT // 2)
rotation_speed = 30  # degrees per second
rotation_angle = 0
num_edges = 5  # Starting with pentagon (5 edges)

# Ball parameters - Scaled up for better visibility
ball_radius = 22
ball_pos = [pentagon_center[0], pentagon_center[1]]  # Will be initialized with random values
ball_vel = [150.0, 0.0]  # Will be initialized with random values

# Slider parameters - Scaled up for better visibility
slider_width = 450
slider_height = 45
slider_x = 15
slider_margin = 90

# Font - Larger sizes for better readability
try:
    font = pygame.font.SysFont('Arial', 48)
    small_font = pygame.font.SysFont('Arial', 36)
except:
    font = pygame.font.Font(None, 48)
    small_font = pygame.font.Font(None, 36)

# Clock for controlling fra
# me rate
clock = pygame.time.Clock()
FPS = 60

# Sound variables
sound_state = 0  # 0: OFF, 1: S1 (coin-collect.mp3), 2: S2 (toast-glass.mp3), 3: S3 (wood-crack.mp3)
try:
    sound_s1 = pygame.mixer.Sound("coin-collect.mp3")
    sound_s2 = pygame.mixer.Sound("toast-glass.mp3")
    sound_s3 = pygame.mixer.Sound("wood-crack.mp3")
    print("Sound effects loaded successfully")
except pygame.error as e:
    # If sound files are not found, create dummy sound objects
    print(f"Error loading sound effects: {e}")
    sound_s1 = None
    sound_s2 = None
    sound_s3 = None

# Music file
music_file = "hktk.mp3"
music_playing = False

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

def draw_neon_glow(vertices, neon_color):
    """Draw neon glow effect for polygon as a whole to avoid gaps at connections"""
    # Pre-calculate center point
    center_x = sum(v[0] for v in vertices) / len(vertices)
    center_y = sum(v[1] for v in vertices) / len(vertices)
    
    # Pre-calculate direction vectors for all vertices
    directions = []
    for vertex in vertices:
        dx = vertex[0] - center_x
        dy = vertex[1] - center_y
        distance = math.sqrt(dx*dx + dy*dy)
        if distance > 0:
            dx /= distance
            dy /= distance
        directions.append((dx, dy))
    
    # Draw multiple nested polygons directly on the screen for better performance
    # Use 5 layers with decreasing size and alpha for a smooth glow effect
    for i in range(5):
        # Calculate alpha and radius for this layer (wider glow)
        alpha = 150 - i * 25  # 150, 125, 100, 75, 50
        alpha = max(30, alpha)  # Minimum alpha of 30
        glow_radius = (5 - i) * 6  # 30, 24, 18, 12, 6 (wider glow)
        
        # Use brighter colors for inner layers and darker for outer layers
        if i == 0:  # Innermost layer
            glow_color = (255, 255, 0)  # Bright yellow
        elif i == 1:
            glow_color = (200, 200, 0)  # Medium yellow
        elif i == 2:
            glow_color = (150, 150, 0)  # Medium-dark yellow
        elif i == 3:
            glow_color = (100, 100, 0)  # Dark yellow
        else:  # Outermost layer
            glow_color = (50, 50, 0)  # Very dark yellow
        
        # Create expanded vertices for glow effect using pre-calculated directions
        glow_vertices = []
        for j, vertex in enumerate(vertices):
            dx, dy = directions[j]
            glow_x = vertex[0] + dx * glow_radius
            glow_y = vertex[1] + dy * glow_radius
            glow_vertices.append((glow_x, glow_y))
        
        # Draw directly to screen with per-pixel alpha (no temporary surface needed)
        # For better performance, we'll draw directly without creating temporary surfaces
        # This is possible by using the gfxdraw module which supports alpha blending
        try:
            # Use gfxdraw.filled_polygon for better performance with alpha blending
            pygame.gfxdraw.filled_polygon(screen, glow_vertices, (*glow_color, alpha))
        except:
            # Fallback to the surface method if gfxdraw is not available or causes issues
            temp_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(temp_surface, (*glow_color, alpha), glow_vertices)
            screen.blit(temp_surface, (0, 0))

def create_slider(x, y, width, height, value, min_val, max_val, dragging=False):
    """Create a slider control"""
    # Draw slider track
    pygame.draw.rect(screen, DARK_GRAY, (x, y, width, height))
    pygame.draw.rect(screen, WHITE, (x, y, width, height), 1)
    
    # Calculate slider position
    slider_pos = x + (value - min_val) / (max_val - min_val) * width
    
    # Draw slider handle (larger and more visible)
    handle_color = BUTTON_HOVER if dragging else BUTTON_COLOR
    handle_width = 20
    handle_height = height + 20
    pygame.draw.rect(screen, handle_color, (slider_pos - handle_width//2, y - (handle_height - height)//2, handle_width, handle_height))
    pygame.draw.rect(screen, WHITE, (slider_pos - handle_width//2, y - (handle_height - height)//2, handle_width, handle_height), 2)


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
        
        # Calculate alpha based on distance (quadratic fade out)
        # Using formula: alpha = 255 * (1 - (distance / max_distance)^2)
        normalized_distance = distance / self.max_distance
        alpha = 255 * (1 - normalized_distance * normalized_distance)
        alpha = max(0, min(255, int(alpha)))  # Clamp between 0 and 255
        
        # Create a temporary surface with per-pixel alpha (1.5x larger)
        temp_surface = pygame.Surface((6, 6), pygame.SRCALPHA)
        
        # Create color with alpha
        color_with_alpha = (*self.color, alpha)
        
        # Draw particle on temporary surface (1.5x larger)
        pygame.draw.circle(temp_surface, color_with_alpha, (3, 3), 3)
        
        # Blit the temporary surface onto the main surface
        surface.blit(temp_surface, (int(self.x) - 3, int(self.y) - 3))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def add_explosion(self, x, y, num_particles=30, max_distance=None):
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
            
            # Random speed (adjust as needed) - 1.5 times faster
            speed = random.uniform(75, 300)
            
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
    global rotation_angle, ball_pos, ball_vel, acceleration, collision_coefficient, random_seed, num_edges, trail_enabled, trail_duration, sound_state, music_enabled, music_channel
    
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
    neon_glow_enabled = True  # Neon glow effect is enabled by default
    button_rect = pygame.Rect(WIDTH - 150, 10, 150, 90)  # 1.5x size
    neon_glow_button_rect = pygame.Rect(WIDTH - 150, 160, 150, 90)  # Moved down to avoid overlapping with Add Edge text
    trail_button_rect = pygame.Rect(WIDTH - 350, 10, 180, 90)  # 1.5x size
    sound_button_rect = pygame.Rect(WIDTH - 580, 10, 200, 90)  # 1.5x size (moved left)
    
    # Music button
    music_button_rect = pygame.Rect(WIDTH - 150, HEIGHT - 100, 140, 90)  # Bottom-right corner
    
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
                    
                # Check if clicking on neon glow toggle button
                if neon_glow_button_rect.collidepoint(mouse_x, mouse_y):
                    neon_glow_enabled = not neon_glow_enabled
                    
                # Check if clicking on trail toggle button
                if trail_button_rect.collidepoint(mouse_x, mouse_y):
                    trail_enabled = not trail_enabled
                    
                # Check if clicking on sound toggle button
                if sound_button_rect.collidepoint(mouse_x, mouse_y):
                    sound_state = (sound_state + 1) % 4  # Cycle through 0, 1, 2, 3
                    
                # Check if clicking on music toggle button
                if music_button_rect.collidepoint(mouse_x, mouse_y):
                    music_enabled = not music_enabled
                    if music_enabled:
                        # Start music mode
                        acceleration = 0
                        collision_coefficient = 1.0
                        # Set ball speed to a higher value for more collisions
                        speed = 5000
                        # Keep the same direction
                        current_speed = math.sqrt(ball_vel[0]**2 + ball_vel[1]**2)
                        if current_speed > 0:
                            ball_vel[0] = ball_vel[0] / current_speed * speed
                            ball_vel[1] = ball_vel[1] / current_speed * speed
                        # Flag to track if we've reached 64 edges and disabled add edge
                        reached_64_edges = False
                        # Reset music text animation
                        music_text_animation_time = 0
                        # Initialize beat detection variables
                        last_beat_time = pygame.time.get_ticks() / 1000.0
                        # Initialize drum detector if available
                        if DRUM_DETECTION_AVAILABLE:
                            # Default BPM hint is 76
                            drum_detector = DrumDetector(bpm_hint=76)
                        # Automatically enable trail in music mode
                        trail_enabled = True
                        # Automatically enable add edge feature in music mode
                        add_edge_enabled = True
                        # Music playback will start when polygon reaches 64 edges
                        music_playing = False
                    else:
                        # Reset to default values
                        acceleration = 9.8
                        collision_coefficient = 1.0
                        # Stop music
                        pygame.mixer.music.stop()
                        music_playing = False
                        # Clear drum detector
                        drum_detector = None
                
                    
            elif event.type == pygame.MOUSEBUTTONUP:
                dragging_acceleration = False
                dragging_collision = False
                dragging_trail_duration = False
                
            elif event.type == pygame.MOUSEMOTION:
                if dragging_acceleration:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    # Calculate new acceleration value
                    relative_x = max(0, min(slider_width, mouse_x - slider_x))
                    acceleration = 0.1 + (relative_x / slider_width) * 19.9  # Range: 0.1 to 20.0
                    
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
        
        # Update ball physics with proper scaling
        dt = 1.0 / FPS  # Time delta
        ball_vel[1] += acceleration * 10 * dt  # Apply acceleration (gravity) with scaling factor
        ball_pos[0] += ball_vel[0] * 10 * dt
        ball_pos[1] += ball_vel[1] * 10 * dt
        
        # Constrain ball to stay within inner polygon
        ball_pos = constrain_ball_to_polygon(ball_pos, pentagon_center, pentagon_radius, ball_radius, rotation_angle, num_edges)
        
        # Check for collisions (for visual effect and sound if needed)
        collision, normal, closest_point = check_collision(ball_pos, ball_radius, vertices)
        if collision:
            # Handle collision response
            handle_collision(ball_vel, normal, collision_coefficient)
            
            # Create particle explosion at collision point
            if closest_point:
                # In music mode, create more particles with longer distance
                if music_enabled:
                    particle_system.add_explosion(closest_point[0], closest_point[1], num_particles=60, max_distance=4.5 * ball_radius * 4)  # 2x distance
                else:
                    particle_system.add_explosion(closest_point[0], closest_point[1])
            
            # Increase edges on collision if toggle is enabled
            if add_edge_enabled:
                num_edges += 1
                
            # Play sound effect based on sound state
            if sound_state == 1 and sound_s1:
                sound_s1.play()
            elif sound_state == 2 and sound_s2:
                sound_s2.play()
            elif sound_state == 3 and sound_s3:
                sound_s3.play()
                
        # Music mode logic
        if music_enabled:
            # Check if polygon has reached 64 edges and we haven't disabled add edge yet
            if num_edges >= 64 and not reached_64_edges:
                # Disable add edge feature
                add_edge_enabled = False
                # Set the flag to indicate we've reached 64 edges and disabled add edge
                reached_64_edges = True
                # Start playing music
                try:
                    pygame.mixer.music.load(music_file)
                    pygame.mixer.music.play(-1)  # Loop indefinitely
                    music_playing = True
                    print("Music started playing")
                except Exception as e:
                    print(f"Error playing music: {e}")
                    # Even if music doesn't play, we continue with the music mode
                    print("Continuing music mode without audio")
                # Change speed to normal value for drum beats
                speed = 150  # Normal speed
                current_speed = math.sqrt(ball_vel[0]**2 + ball_vel[1]**2)
                if current_speed > 0:
                    # Scale velocity to match target speed while keeping direction
                    scale_factor = speed / current_speed
                    ball_vel[0] *= scale_factor
                    ball_vel[1] *= scale_factor
            
            # Update music text animation time
            music_text_animation_time += dt
            
            # Real-time beat detection using drum detector if available
            current_time = pygame.time.get_ticks() / 1000.0  # Convert to seconds
            
            # Use drum detector if available, otherwise use simulated beats
            global prev_audio_frame  # Access the global variable
            if DRUM_DETECTION_AVAILABLE and drum_detector and music_playing:
                # Get audio data from pygame mixer
                # Note: This is a simplified approach. In a real implementation, you would
                # need to access the raw audio data from the music file.
                # For now, we'll generate synthetic audio data for demonstration.
                # In practice, you would use pygame.mixer.get_raw() or similar.
                
                # Generate synthetic audio frame for demonstration
                # In a real implementation, this would come from the actual audio stream
                # Generate more dynamic audio data to simulate actual music
                # Create a more complex audio signal with varying energy levels
                t = current_time
                # Base frequency components
                freq1 = 220  # A3 note
                freq2 = 440  # A4 note
                freq3 = 880  # A5 note
                
                # Generate time array for the frame
                frame_samples = 1024
                sample_rate = 44100
                time_array = np.linspace(t, t + frame_samples/sample_rate, frame_samples)
                
                # Generate composite waveform with harmonics
                audio_frame = (
                    np.sin(2 * np.pi * freq1 * time_array) * 0.3 +
                    np.sin(2 * np.pi * freq2 * time_array) * 0.2 +
                    np.sin(2 * np.pi * freq3 * time_array) * 0.1 +
                    np.random.normal(0, 0.05, frame_samples)  # Add some noise
                )
                
                # Occasionally add drum-like transients to simulate beats
                if np.random.random() < 0.05:  # 5% chance of a beat
                    # Add a transient (sharp spike) to simulate a drum hit
                    transient_length = 50
                    transient = np.exp(-np.linspace(0, 5, transient_length)) * np.random.random()
                    if len(audio_frame) > transient_length:
                        audio_frame[:transient_length] += transient * 2.0
                
                # Detect beat using drum detector with previous frame for spectral flux
                beat_detected = drum_detector.detect_beat(audio_frame, current_time, prev_audio_frame)
                
                # Store current frame for next iteration
                prev_audio_frame = audio_frame.copy()
            else:
                # Fallback to simulated beats if drum detector is not available
                if current_time - last_beat_time >= 0.5:
                    # Simulate a beat detection
                    beat_detected = True
                    # Update last beat time
                    last_beat_time = current_time
                else:
                    beat_detected = False
                
            # If a beat is detected and we've reached 64 edges, adjust the ball's speed to ensure it collides with the polygon
            if beat_detected and reached_64_edges:
                # Calculate distance to center
                dx = ball_pos[0] - pentagon_center[0]
                dy = ball_pos[1] - pentagon_center[1]
                distance_to_center = math.sqrt(dx*dx + dy*dy)
                
                # For a circle approximation, we want the ball to travel a certain distance in one beat
                # We'll use a fixed distance for simplicity
                target_distance = 200  # Adjust this value as needed
                
                # Time between beats (we'll use a fixed value since we can't access actual audio data)
                beat_time = 0.5  # 0.5 seconds between beats
                
                # Speed needed to travel target distance in one beat
                target_speed = target_distance / beat_time
                
                # Adjust current speed to match target speed (keep direction)
                current_speed = math.sqrt(ball_vel[0]**2 + ball_vel[1]**2)
                if current_speed > 0:
                    # Scale velocity to match target speed
                    scale_factor = target_speed / current_speed
                    ball_vel[0] *= scale_factor
                    ball_vel[1] *= scale_factor
                    
                    # After adjusting speed, check for immediate collision
                    # This will create the visual effect of the ball bouncing on the beat
                    collision, normal, closest_point = check_collision(ball_pos, ball_radius, vertices)
                    if collision:
                        # Handle collision response
                        handle_collision(ball_vel, normal, collision_coefficient)
                        
                        # Create particle explosion at collision point
                        if closest_point:
                            # In music mode, create more particles with longer distance
                            if music_enabled:
                                particle_system.add_explosion(closest_point[0], closest_point[1], num_particles=60, max_distance=4.5 * ball_radius * 4)  # 2x distance
                            else:
                                particle_system.add_explosion(closest_point[0], closest_point[1])
                
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
        
        # Draw neon glow effect for polygon edges if enabled
        if neon_glow_enabled:
            draw_neon_glow(vertices, NEON_COLORS[0])
        
        # Draw pentagon filled with black
        pygame.draw.polygon(screen, BLACK, vertices)
        
        # Draw pentagon white border
        pygame.draw.polygon(screen, WHITE, vertices, 10)
        
        # Draw trail if enabled
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
        
        # Draw ball (change color to blue when music is enabled)
        ball_color = (0, 0, 255) if music_enabled else RED  # Blue when music is enabled
        pygame.draw.circle(screen, ball_color, (int(ball_pos[0]), int(ball_pos[1])), ball_radius)
        
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
        screen.blit(state_text, (button_rect.x - 20, button_rect.y + button_rect.height + 10))
        
        # Draw Neon Glow button
        neon_glow_button_color = BUTTON_HOVER if neon_glow_button_rect.collidepoint(pygame.mouse.get_pos()) else BUTTON_COLOR
        pygame.draw.rect(screen, neon_glow_button_color, neon_glow_button_rect)
        pygame.draw.rect(screen, WHITE, neon_glow_button_rect, 2)
        
        # Draw neon glow button text
        neon_glow_button_text = font.render("GLOW", True, WHITE)
        neon_glow_text_rect = neon_glow_button_text.get_rect(center=neon_glow_button_rect.center)
        screen.blit(neon_glow_button_text, neon_glow_text_rect)
        
        # Draw neon glow toggle state text
        neon_glow_state_text = small_font.render(f"Glow {'ON' if neon_glow_enabled else 'OFF'}", True, WHITE)
        screen.blit(neon_glow_state_text, (neon_glow_button_rect.x - 20, neon_glow_button_rect.y + neon_glow_button_rect.height + 10))
        
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
        screen.blit(trail_state_text, (trail_button_rect.x + 20, trail_button_rect.y + trail_button_rect.height + 10))
        
        # Draw Sound button
        sound_button_color = BUTTON_HOVER if sound_button_rect.collidepoint(pygame.mouse.get_pos()) else BUTTON_COLOR
        pygame.draw.rect(screen, sound_button_color, sound_button_rect)
        pygame.draw.rect(screen, WHITE, sound_button_rect, 2)
        
        # Draw sound button text based on sound state
        if sound_state == 0:
            sound_text = "OFF"
        elif sound_state == 1:
            sound_text = "S1"
        elif sound_state == 2:
            sound_text = "S2"
        else:  # sound_state == 3
            sound_text = "S3"
            
        sound_button_text = font.render(f"SOUND:{sound_text}", True, WHITE)
        sound_text_rect = sound_button_text.get_rect(center=sound_button_rect.center)
        screen.blit(sound_button_text, sound_text_rect)
        
        # Draw Music button
        music_button_color = BUTTON_HOVER if music_button_rect.collidepoint(pygame.mouse.get_pos()) else BUTTON_COLOR
        pygame.draw.rect(screen, music_button_color, music_button_rect)
        pygame.draw.rect(screen, WHITE, music_button_rect, 2)
        
        # Draw music button text
        music_button_text = font.render("MUSIC", True, WHITE)
        music_text_rect = music_button_text.get_rect(center=music_button_rect.center)
        screen.blit(music_button_text, music_text_rect)
        
        # Draw music toggle state text
        music_state_text = small_font.render(f"Music {'ON' if music_enabled else 'OFF'}", True, WHITE)
        screen.blit(music_state_text, (music_button_rect.x - 20, music_button_rect.y + music_button_rect.height + 10))
        
        
        # Draw UI sliders and text
        acc_slider_y = 30
        col_slider_y = 30 + slider_margin
        trail_slider_y = 30 + 2 * slider_margin
        
        # Acceleration slider
        create_slider(slider_x, acc_slider_y, slider_width, slider_height, 
                      acceleration, 0.1, 20.0, dragging_acceleration)
        acc_label = font.render("Acceleration (a):", True, WHITE)
        acc_value = font.render(f"{acceleration:.1f}", True, WHITE)
        screen.blit(acc_label, (slider_x + slider_width + 20, acc_slider_y + 10))
        screen.blit(acc_value, (slider_x + slider_width + 300, acc_slider_y + 10))
        
        # Collision coefficient slider
        create_slider(slider_x, col_slider_y, slider_width, slider_height, 
                      collision_coefficient, 0.0, 1.0, dragging_collision)
        col_label = font.render("Collision (e):", True, WHITE)
        col_value = font.render(f"{collision_coefficient:.2f}", True, WHITE)
        screen.blit(col_label, (slider_x + slider_width + 20, col_slider_y + 10))
        screen.blit(col_value, (slider_x + slider_width + 300, col_slider_y + 10))
        
        # Trail duration slider
        create_slider(slider_x, trail_slider_y, slider_width, slider_height, 
                      trail_duration, 0.5, 10.0, dragging_trail_duration)
        trail_label = font.render("Trail Duration:", True, WHITE)
        trail_value = font.render(f"{trail_duration:.1f}s", True, WHITE)
        screen.blit(trail_label, (slider_x + slider_width + 20, trail_slider_y + 10))
        screen.blit(trail_value, (slider_x + slider_width + 300, trail_slider_y + 10))
        
        # Display current number of edges in bottom-left corner
        edges_text = small_font.render(f"Edges: {num_edges}", True, WHITE)
        screen.blit(edges_text, (10, HEIGHT - 50))
        
        # Display animated "Music！！！" text when music is enabled
        if music_enabled:
            # Calculate animation progress (0.0 to 1.0)
            animation_progress = min(1.0, music_text_animation_time / music_text_animation_duration)
            
            # Calculate text size to occupy 9/16 of window area
            # 9/16 of window height
            text_height = int(HEIGHT * 9 / 16)
            # Create a large font for the text (use default font)
            try:
                font_size = min(text_height // 2, 200)  # Cap the font size at 200
                large_font = pygame.font.SysFont('Arial', font_size)
            except:
                # Fallback to default font if Arial is not available
                large_font = pygame.font.Font(None, font_size)
            music_text = large_font.render("Music!!!", True, WHITE)
            
            # Calculate text position for sliding animation
            # Start from below the screen (y = HEIGHT) and move to above the screen (y = -text_height)
            start_y = HEIGHT
            end_y = -text_height
            current_y = start_y + (end_y - start_y) * animation_progress
            
            # Center the text horizontally
            music_text_rect = music_text.get_rect(centerx=WIDTH // 2, y=int(current_y))
            screen.blit(music_text, music_text_rect)
        
        # Update display
        pygame.display.flip()
        
        # Control frame rate
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
