shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

// Terrain heightmap
uniform sampler2D heightmap : filter_linear_mipmap, repeat_enable;
uniform float height_scale : hint_range(0.0, 100.0) = 0.0;
uniform float terrain_size = 500.0;

// Texture layers
uniform sampler2D albedo_tex_1 : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normal_tex_1 : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D roughness_tex_1 : filter_linear_mipmap_anisotropic, repeat_enable;
uniform float uv_scale_1 : hint_range(1.0, 100.0) = 20.0;
uniform float height_min_1 : hint_range(-50.0, 50.0) = -10.0;
uniform float height_max_1 : hint_range(-50.0, 50.0) = 8.0;

uniform sampler2D albedo_tex_2 : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normal_tex_2 : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D roughness_tex_2 : filter_linear_mipmap_anisotropic, repeat_enable;
uniform float uv_scale_2 : hint_range(1.0, 100.0) = 25.0;
uniform float height_min_2 : hint_range(-50.0, 50.0) = 5.0;
uniform float height_max_2 : hint_range(-50.0, 50.0) = 20.0;

uniform sampler2D albedo_tex_3 : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normal_tex_3 : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D roughness_tex_3 : filter_linear_mipmap_anisotropic, repeat_enable;
uniform float uv_scale_3 : hint_range(1.0, 100.0) = 15.0;
uniform float height_min_3 : hint_range(-50.0, 100.0) = 15.0;
uniform float height_max_3 : hint_range(-50.0, 100.0) = 50.0;

uniform sampler2D albedo_tex_4 : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normal_tex_4 : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D roughness_tex_4 : filter_linear_mipmap_anisotropic, repeat_enable;
uniform float uv_scale_4 : hint_range(1.0, 100.0) = 30.0;
uniform float height_min_4 : hint_range(-50.0, 150.0) = 40.0;
uniform float height_max_4 : hint_range(-50.0, 150.0) = 100.0;

uniform float blend_sharpness : hint_range(0.1, 10.0) = 2.0;
uniform float slope_threshold : hint_range(0.0, 1.0) = 0.7;
uniform float slope_blend : hint_range(0.0, 0.5) = 0.2;
uniform bool use_triplanar = false;
uniform float triplanar_sharpness : hint_range(0.1, 10.0) = 4.0;

void vertex() {
    // Heightmap displacement
    float h = texture(heightmap, UV).r * height_scale;
    VERTEX.y += h;
}

void fragment() {
    // Simple grass texture with fallback
    vec2 uv = UV * uv_scale_1;
    vec4 tex = texture(albedo_tex_1, uv);

    // If texture is black/missing, use a default green color
    vec3 albedo = tex.rgb;
    if (length(albedo) < 0.01) {
        albedo = vec3(0.2, 0.5, 0.15); // Fallback grass green
    }

    ALBEDO = albedo;
    ROUGHNESS = 0.8;
    METALLIC = 0.0;
}
