shader_type spatial;
render_mode cull_disabled;

uniform float wind_strength : hint_range(0.0, 2.0) = 0.3;
uniform float wind_speed : hint_range(0.0, 5.0) = 1.5;
uniform float wind_turbulence : hint_range(0.0, 2.0) = 0.5;
uniform vec2 wind_direction = vec2(1.0, 0.5);
uniform sampler2D albedo_texture : source_color;

varying float height_factor;

void vertex() {
    // Calculate height factor (0 at base, 1 at top)
    height_factor = clamp(VERTEX.y / 2.0, 0.0, 1.0);

    // Only sway the top parts
    if (height_factor > 0.1) {
        vec3 world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;

        // Main wind wave
        float wind_wave = sin(TIME * wind_speed + world_pos.x * 0.5 + world_pos.z * 0.3);

        // Turbulence
        float turb = sin(TIME * wind_speed * 2.3 + world_pos.x * 1.2) * wind_turbulence;
        turb += cos(TIME * wind_speed * 1.7 + world_pos.z * 0.9) * wind_turbulence * 0.5;

        // Combined displacement
        float displacement = (wind_wave + turb) * wind_strength * height_factor * height_factor;

        // Apply wind direction
        vec2 wind_dir = normalize(wind_direction);
        VERTEX.x += displacement * wind_dir.x;
        VERTEX.z += displacement * wind_dir.y;

        // Slight vertical bob
        VERTEX.y += sin(TIME * wind_speed * 0.5 + world_pos.x) * wind_strength * height_factor * 0.1;
    }
}

void fragment() {
    vec4 tex_color = texture(albedo_texture, UV);
    ALBEDO = tex_color.rgb;
    ALPHA = tex_color.a;
    ALPHA_SCISSOR_THRESHOLD = 0.5;
}
