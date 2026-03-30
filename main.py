import pygame
import sys
import math

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

# Pentagon parameters
pentagon_radius = 200
pentagon_center = (WIDTH // 2, HEIGHT // 2)
rotation_speed = 30  # degrees per second
rotation_angle = 0

# Ball parameters
ball_radius = 8
ball_pos = [pentagon_center[0], pentagon_center[1]]
ball_vel = [150.0, 0.0]  # Initial horizontal velocity

# Slider parameters
slider_width = 200
slider_height = 20
slider_x = 10
slider_margin = 40

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


def get_inner_pentagon_vertices(center, outer_radius, inner_radius, angle):
    """Calculate vertices of inner pentagon for ball constraint"""
    vertices = []
    for i in range(5):
        vertex_angle = math.radians(angle + i * 72)
        x = center[0] + inner_radius * math.cos(vertex_angle)
        y = center[1] + inner_radius * math.sin(vertex_angle)
        vertices.append((x, y))
    return vertices


def constrain_ball_to_pentagon(ball_pos, center, outer_radius, ball_radius, angle):
    """Constrain ball position to stay within inner pentagon"""
    inner_radius = outer_radius - ball_radius
    
    # Get inner pentagon vertices
    inner_vertices = get_inner_pentagon_vertices(center, outer_radius, inner_radius, angle)
    
    # Check if ball is outside inner pentagon
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
    """Check if ball collides with any pentagon edge or vertex"""
    # First check for edge collisions
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
    
    # Then check for vertex collisions
    for vertex in vertices:
        distance = math.sqrt((ball_pos[0] - vertex[0])**2 + (ball_pos[1] - vertex[1])**2)
        if distance <= ball_radius:
            # Calculate normal vector from vertex to ball (outward from pentagon)
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

def main():
    global rotation_angle, ball_pos, ball_vel, acceleration, collision_coefficient
    
    # Slider dragging states
    dragging_acceleration = False
    dragging_collision = False
    
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
                
            elif event.type == pygame.MOUSEBUTTONUP:
                dragging_acceleration = False
                dragging_collision = False
                
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
        
        # Constrain ball to stay within inner pentagon
        ball_pos = constrain_ball_to_pentagon(ball_pos, pentagon_center, pentagon_radius, ball_radius, rotation_angle)
        
        # Check for collisions (for visual effect and sound if needed)
        collision, normal, closest_point = check_collision(ball_pos, ball_radius, vertices)
        if collision:
            # Handle collision response
            handle_collision(ball_vel, normal, collision_coefficient)
        
        # Clear screen
        screen.fill(BLACK)
        
        # Draw pentagon
        pygame.draw.polygon(screen, DARK_GRAY, vertices)
        pygame.draw.polygon(screen, WHITE, vertices, 2)
        
        # Draw ball
        pygame.draw.circle(screen, RED, (int(ball_pos[0]), int(ball_pos[1])), ball_radius)
        
        # Draw UI sliders and text
        acc_slider_y = 20
        col_slider_y = 20 + slider_margin
        
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
        
        # Update display
        pygame.display.flip()
        
        # Control frame rate
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()