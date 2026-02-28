shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back;

uniform vec3 water_color : source_color = vec3(0.1, 0.3, 0.5);
uniform vec3 foam_color : source_color = vec3(0.8, 0.9, 1.0);
uniform float wave_speed : hint_range(0.0, 2.0) = 0.5;
uniform float wave_height : hint_range(0.0, 1.0) = 0.1;
uniform float wave_frequency : hint_range(0.0, 10.0) = 2.0;
uniform float transparency : hint_range(0.0, 1.0) = 0.6;
uniform float fresnel_power : hint_range(0.0, 10.0) = 3.0;

varying vec3 world_pos;

void vertex() {
    world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;

    // Animated waves
    float wave1 = sin(world_pos.x * wave_frequency + TIME * wave_speed) * wave_height;
    float wave2 = sin(world_pos.z * wave_frequency * 0.7 + TIME * wave_speed * 1.3) * wave_height * 0.5;
    float wave3 = sin((world_pos.x + world_pos.z) * wave_frequency * 0.5 + TIME * wave_speed * 0.8) * wave_height * 0.3;

    VERTEX.y += wave1 + wave2 + wave3;

    // Update normal for waves
    float delta = 0.1;
    float hL = sin((world_pos.x - delta) * wave_frequency + TIME * wave_speed) * wave_height;
    float hR = sin((world_pos.x + delta) * wave_frequency + TIME * wave_speed) * wave_height;
    float hD = sin((world_pos.z - delta) * wave_frequency * 0.7 + TIME * wave_speed * 1.3) * wave_height * 0.5;
    float hU = sin((world_pos.z + delta) * wave_frequency * 0.7 + TIME * wave_speed * 1.3) * wave_height * 0.5;

    NORMAL = normalize(vec3(hL - hR, delta * 2.0, hD - hU));
}

void fragment() {
    // Fresnel effect for reflection-like appearance
    float fresnel = pow(1.0 - dot(NORMAL, VIEW), fresnel_power);

    // Base water color with fresnel
    vec3 color = mix(water_color, foam_color, fresnel * 0.5);

    // Subtle sparkle effect
    float sparkle = pow(max(0.0, dot(reflect(-VIEW, NORMAL), vec3(0.5, 1.0, 0.5))), 32.0);
    color += vec3(sparkle) * 0.3;

    ALBEDO = color;
    ROUGHNESS = 0.1;
    METALLIC = 0.3;
    ALPHA = mix(transparency, 1.0, fresnel * 0.3);
}
