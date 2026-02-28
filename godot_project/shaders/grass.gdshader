shader_type spatial;
render_mode cull_disabled, depth_draw_opaque, diffuse_burley, specular_schlick_ggx;

// Grass appearance
uniform sampler2D grass_texture : source_color, filter_linear_mipmap_anisotropic;
uniform vec3 grass_color_base : source_color = vec3(0.15, 0.4, 0.1);
uniform vec3 grass_color_tip : source_color = vec3(0.4, 0.6, 0.2);
uniform float color_variation : hint_range(0.0, 0.3) = 0.1;
uniform float alpha_scissor : hint_range(0.0, 1.0) = 0.3;

// Wind animation
uniform float wind_strength : hint_range(0.0, 2.0) = 0.5;
uniform float wind_speed : hint_range(0.0, 5.0) = 1.5;
uniform vec2 wind_direction = vec2(1.0, 0.5);
uniform float wind_turbulence : hint_range(0.0, 1.0) = 0.3;
uniform sampler2D wind_noise : filter_linear_mipmap, repeat_enable;
uniform float wind_noise_scale : hint_range(0.01, 0.5) = 0.1;

// LOD and distance fade
uniform float fade_start : hint_range(10.0, 200.0) = 50.0;
uniform float fade_end : hint_range(20.0, 300.0) = 80.0;

// Subsurface scattering approximation
uniform float subsurface_strength : hint_range(0.0, 1.0) = 0.5;
uniform vec3 subsurface_color : source_color = vec3(0.5, 0.8, 0.3);

// Interaction
uniform vec3 interaction_point = vec3(0.0);
uniform float interaction_radius : hint_range(0.0, 5.0) = 2.0;
uniform float interaction_strength : hint_range(0.0, 2.0) = 1.0;

varying float height_factor;
varying vec3 world_pos;

void vertex() {
    // ========== Y-AXIS BILLBOARD ==========
    // This makes each grass blade face the camera horizontally (fixes "line" appearance)

    // Get camera position in world space
    vec3 cam_world_pos = (INV_VIEW_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;

    // Get instance origin in world space
    vec3 instance_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;

    // Direction from grass to camera (horizontal only - Y-axis billboard)
    vec3 to_camera = cam_world_pos - instance_origin;
    to_camera.y = 0.0; // Keep grass upright
    float dist_to_cam = length(to_camera);
    to_camera = normalize(to_camera);

    // Create billboard basis vectors
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), to_camera));
    vec3 up = vec3(0.0, 1.0, 0.0);

    // Billboard transform: X goes to right vector, Y stays up, Z faces camera
    vec3 billboard_pos = VERTEX.x * right + VERTEX.y * up;

    // Get original scale from model matrix
    float scale_x = length(vec3(MODEL_MATRIX[0][0], MODEL_MATRIX[1][0], MODEL_MATRIX[2][0]));
    float scale_y = length(vec3(MODEL_MATRIX[0][1], MODEL_MATRIX[1][1], MODEL_MATRIX[2][1]));

    // Apply billboard position with scale
    VERTEX = billboard_pos;

    // ========== WIND ANIMATION ==========
    // Height factor (0 at base, 1 at tip)
    height_factor = clamp(VERTEX.y / 0.4, 0.0, 1.0);

    // Get world position for wind sampling
    world_pos = instance_origin + billboard_pos;

    // Wind calculation
    float time = TIME * wind_speed;
    vec2 wind_uv = world_pos.xz * wind_noise_scale + normalize(wind_direction) * time * 0.1;
    float noise_sample = texture(wind_noise, wind_uv).r;

    // Main wind wave
    vec2 wind_dir = normalize(wind_direction);
    float wind_wave = sin(dot(world_pos.xz, wind_dir) * 0.5 + time) * 0.5 + 0.5;

    // Combine wind effects - only affect top of grass
    float wind = (wind_wave + noise_sample * wind_turbulence) * wind_strength * height_factor * height_factor;

    // Apply wind displacement (in world XZ direction, then project to billboard)
    VERTEX.x += wind * 0.3; // Wind bends the grass in the "right" direction of billboard

    // Store world position for fragment shader
    world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
    // Gradient color from base to tip
    vec3 grass_color = mix(grass_color_base, grass_color_tip, height_factor);

    // Sample texture if available
    vec4 tex_color = texture(grass_texture, UV);
    grass_color *= tex_color.rgb;

    // Simple alpha
    float alpha = tex_color.a;
    if (alpha < alpha_scissor) {
        discard;
    }

    ALBEDO = grass_color;
    ROUGHNESS = 0.8;
    METALLIC = 0.0;

    // Subsurface scattering effect
    BACKLIGHT = subsurface_color * subsurface_strength * height_factor;
}
