import pygame
import sys
import math

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ball Within Rotating Pentagon")

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

# Pentagon parameters
pentagon_radius = 200
pentagon_center = (WIDTH // 2, HEIGHT // 2)
rotation_speed = 30  # degrees per second
rotation_angle = 0

# Ball parameters
ball_radius = 8
ball_pos = [pentagon_center[0], pentagon_center[1]]
ball_vel = [150.0, 0.0]  # Initial horizontal velocity

# Button parameters
button_width = 120
button_height = 40
button_margin = 10

# Font
try:
    font = pygame.font.SysFont('Arial', 20)
except:
    font = pygame.font.Font(None, 20)

# Clock for controlling frame rate
clock = pygame.time.Clock()
FPS = 60

def get_pentagon_vertices(center, radius, angle):
    """Calculate the vertices of a regular pentagon"""
    vertices = []
    for i in range(5):
        # Calculate angle for each vertex (72 degrees apart)
        vertex_angle = math.radians(angle + i * 72)
        x = center[0] + radius * math.cos(vertex_angle)
        y = center[1] + radius * math.sin(vertex_angle)
        vertices.append((x, y))
    return vertices

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
    """Check if ball collides with any pentagon edge"""
    for i in range(5):
        start = vertices[i]
        end = vertices[(i + 1) % 5]
        
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
    
    return False, None, None

def handle_collision(ball_vel, normal, collision_coefficient):
    """Handle collision response"""
    # Dot product of velocity and normal
    dot_product = ball_vel[0] * normal[0] + ball_vel[1] * normal[1]
    
    # Apply collision response
    ball_vel[0] = ball_vel[0] - 2 * dot_product * normal[0] * collision_coefficient
    ball_vel[1] = ball_vel[1] - 2 * dot_product * normal[1] * collision_coefficient

def create_button(x, y, width, height, text, hover=False):
    """Create a button with text"""
    color = BUTTON_HOVER if hover else BUTTON_COLOR
    pygame.draw.rect(screen, color, (x, y, width, height))
    pygame.draw.rect(screen, WHITE, (x, y, width, height), 2)
    
    text_surface = font.render(text, True, WHITE)
    text_rect = text_surface.get_rect(center=(x + width // 2, y + height // 2))
    screen.blit(text_surface, text_rect)

def main():
    global rotation_angle, ball_pos, ball_vel, acceleration, collision_coefficient
    
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                
                # Check acceleration buttons
                if 10 <= mouse_x <= 130 and 10 <= mouse_y <= 50:
                    acceleration = max(0.1, acceleration - 0.1)
                elif 150 <= mouse_x <= 270 and 10 <= mouse_y <= 50:
                    acceleration = min(10.0, acceleration + 0.1)
                
                # Check collision coefficient buttons
                elif 10 <= mouse_x <= 130 and 60 <= mouse_y <= 100:
                    collision_coefficient = max(0.0, collision_coefficient - 0.1)
                elif 150 <= mouse_x <= 270 and 60 <= mouse_y <= 100:
                    collision_coefficient = min(1.0, collision_coefficient + 0.1)
        
        # Update rotation angle
        rotation_angle += rotation_speed / FPS
        if rotation_angle >= 360:
            rotation_angle -= 360
        
        # Get current pentagon vertices
        vertices = get_pentagon_vertices(pentagon_center, pentagon_radius, rotation_angle)
        
        # Update ball physics
        ball_vel[1] += acceleration  # Apply acceleration (gravity)
        ball_pos[0] += ball_vel[0] / FPS
        ball_pos[1] += ball_vel[1] / FPS
        
        # Check for collisions
        collision, normal, closest_point = check_collision(ball_pos, ball_radius, vertices)
        if collision:
            # Move ball to just outside the collision point
            ball_pos[0] = closest_point[0] + normal[0] * ball_radius
            ball_pos[1] = closest_point[1] + normal[1] * ball_radius
            
            # Handle collision response
            handle_collision(ball_vel, normal, collision_coefficient)
        
        # Clear screen
        screen.fill(BLACK)
        
        # Draw pentagon
        pygame.draw.polygon(screen, DARK_GRAY, vertices)
        pygame.draw.polygon(screen, WHITE, vertices, 2)
        
        # Draw ball
        pygame.draw.circle(screen, RED, (int(ball_pos[0]), int(ball_pos[1])), ball_radius)
        
        # Draw UI buttons and text
        mouse_x, mouse_y = pygame.mouse.get_pos()
        
        # Acceleration buttons
        create_button(10, 10, button_width, button_height, "a - 0.1", 
                     10 <= mouse_x <= 130 and 10 <= mouse_y <= 50)
        create_button(150, 10, button_width, button_height, "a + 0.1", 
                     150 <= mouse_x <= 270 and 10 <= mouse_y <= 50)
        
        # Collision coefficient buttons
        create_button(10, 60, button_width, button_height, "e - 0.1", 
                     10 <= mouse_x <= 130 and 60 <= mouse_y <= 100)
        create_button(150, 60, button_width, button_height, "e + 0.1", 
                     150 <= mouse_x <= 270 and 60 <= mouse_y <= 100)
        
        # Display current values
        acc_text = font.render(f"a = {acceleration:.1f}", True, WHITE)
        col_text = font.render(f"e = {collision_coefficient:.1f}", True, WHITE)
        screen.blit(acc_text, (290, 25))
        screen.blit(col_text, (290, 75))
        
        # Update display
        pygame.display.flip()
        
        # Control frame rate
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()