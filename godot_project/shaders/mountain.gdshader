shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

// Rock textures
uniform sampler2D rock_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rock_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rock_roughness : filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec3 rock_tint : source_color = vec3(0.45, 0.42, 0.38);
uniform float rock_uv_scale : hint_range(0.01, 0.5) = 0.1;

// Snow textures
uniform sampler2D snow_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D snow_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D snow_roughness : filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec3 snow_tint : source_color = vec3(0.95, 0.97, 1.0);
uniform float snow_uv_scale : hint_range(0.01, 0.5) = 0.15;

// Snow coverage
uniform float snow_height : hint_range(0.0, 200.0) = 40.0;
uniform float snow_blend_range : hint_range(1.0, 30.0) = 10.0;
uniform float snow_slope_threshold : hint_range(0.0, 1.0) = 0.5;
uniform float snow_slope_blend : hint_range(0.0, 0.5) = 0.2;

// Detail noise
uniform sampler2D detail_noise : filter_linear_mipmap, repeat_enable;
uniform float detail_scale : hint_range(0.001, 0.1) = 0.02;
uniform float detail_strength : hint_range(0.0, 0.5) = 0.15;

uniform float triplanar_sharpness : hint_range(0.5, 10.0) = 4.0;

varying vec3 world_pos;
varying vec3 world_normal;

void vertex() {
    world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
    vec3 normal = normalize(world_normal);

    // Simple triplanar blend weights
    vec3 blend = pow(abs(normal), vec3(triplanar_sharpness));
    blend /= (blend.x + blend.y + blend.z);

    // Sample rock texture with triplanar
    vec3 rock_x = texture(rock_albedo, world_pos.zy * rock_uv_scale).rgb;
    vec3 rock_y = texture(rock_albedo, world_pos.xz * rock_uv_scale).rgb;
    vec3 rock_z = texture(rock_albedo, world_pos.xy * rock_uv_scale).rgb;
    vec3 rock_color = (rock_x * blend.x + rock_y * blend.y + rock_z * blend.z) * rock_tint;

    // Sample snow texture with triplanar
    vec3 snow_x = texture(snow_albedo, world_pos.zy * snow_uv_scale).rgb;
    vec3 snow_y = texture(snow_albedo, world_pos.xz * snow_uv_scale).rgb;
    vec3 snow_z = texture(snow_albedo, world_pos.xy * snow_uv_scale).rgb;
    vec3 snow_color = (snow_x * blend.x + snow_y * blend.y + snow_z * blend.z) * snow_tint;

    // Height-based snow factor
    float height_factor = smoothstep(snow_height - snow_blend_range, snow_height + snow_blend_range, world_pos.y);

    // Slope-based factor (snow on flat surfaces)
    float slope = 1.0 - abs(normal.y);
    float slope_factor = 1.0 - smoothstep(snow_slope_threshold - snow_slope_blend, snow_slope_threshold + snow_slope_blend, slope);

    // Detail noise
    float detail = texture(detail_noise, world_pos.xz * detail_scale).r;

    // Combined snow factor
    float snow_factor = clamp(height_factor * slope_factor + detail * detail_strength, 0.0, 1.0);

    // Blend rock and snow
    vec3 final_color = mix(rock_color, snow_color, snow_factor);

    // Sample roughness
    float rock_rough = texture(rock_roughness, world_pos.xz * rock_uv_scale).r;
    float snow_rough = texture(snow_roughness, world_pos.xz * snow_uv_scale).r;
    float final_roughness = mix(rock_rough, snow_rough, snow_factor);

    ALBEDO = final_color;
    ROUGHNESS = final_roughness;
    METALLIC = 0.0;
}
