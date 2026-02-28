shader_type sky;
render_mode use_half_res_pass;

// Stylized Sky Shader for Godot 4
// From gdquest-demos/godot-4-stylized-sky (MIT License)

group_uniforms clouds;

uniform sampler2D cloud_shape_sampler : filter_linear_mipmap, repeat_enable;
uniform sampler2D cloud_noise_sampler : filter_linear_mipmap, repeat_enable;
uniform sampler2D cloud_curves : repeat_disable;

uniform int clouds_samples : hint_range(8, 32, 8) = 16;
uniform int shadow_sample : hint_range(1, 4, 1) = 2;

uniform float clouds_density : hint_range(0.0, 1.0, 0.1) = 0.5;
uniform float clouds_scale : hint_range(0.5, 1.5, 0.1) = 1.0;
uniform float clouds_smoothness : hint_range(0.01, 0.1, 0.01) = 0.035;
uniform vec3 clouds_light_color : source_color = vec3(1.0);
uniform float clouds_shadow_intensity : hint_range(0.1, 10.0, 0.1) = 3.0;

group_uniforms sky;

uniform vec3 top_color : source_color = vec3(0.35, 0.45, 0.75);
uniform vec3 bottom_color : source_color = vec3(0.8, 0.55, 0.3);
uniform vec3 sun_scatter : source_color = vec3(1.0, 0.5, 0.2);

group_uniforms sun;

uniform float sun_size : hint_range(0.01, 0.2, 0.01) = 0.05;
uniform vec3 sun_color : source_color = vec3(1.0, 0.9, 0.7);
uniform float sun_intensity : hint_range(1.0, 10.0, 0.5) = 3.0;

group_uniforms stars;

uniform float stars_intensity : hint_range(0.0, 5.0, 0.1) = 0.0;

// Hash functions for noise
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

float hash3(vec3 p) {
    return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453123);
}

vec3 hash33(vec3 p) {
    p = vec3(dot(p, vec3(127.1, 311.7, 74.7)),
             dot(p, vec3(269.5, 183.3, 246.1)),
             dot(p, vec3(113.5, 271.9, 124.6)));
    return fract(sin(p) * 43758.5453123);
}

// Voronoi for stars
vec3 voronoi(vec3 x) {
    vec3 p = floor(x);
    vec3 f = fract(x);

    float id = 0.0;
    vec2 res = vec2(100.0);
    for(int k = -1; k <= 1; k++)
    for(int j = -1; j <= 1; j++)
    for(int i = -1; i <= 1; i++) {
        vec3 b = vec3(float(i), float(j), float(k));
        vec3 r = b - f + hash33(p + b);
        float d = dot(r, r);
        if(d < res.x) {
            id = dot(p + b, vec3(1.0, 57.0, 113.0));
            res = vec2(d, res.x);
        } else if(d < res.y) {
            res.y = d;
        }
    }
    return vec3(sqrt(res), abs(id));
}

// Cloud density sampling
float sample_cloud_density(vec3 p, float height_progress) {
    float time_offset = TIME * 0.02;
    float time_offset_small = TIME * -0.03;

    // Sample noise textures
    vec2 uv_main = p.xy * clouds_scale + time_offset;
    vec2 uv_detail = p.xy * clouds_scale * 3.0 + time_offset_small;

    float shape = texture(cloud_shape_sampler, uv_main).r;
    float noise = texture(cloud_noise_sampler, uv_detail).r;
    float height_curve = texture(cloud_curves, vec2(height_progress, 0.5)).r;

    float cloud = shape * noise * height_curve;
    float threshold = 1.0 - clouds_density;

    return smoothstep(threshold - clouds_smoothness, threshold + clouds_smoothness, cloud);
}

// Raymarched clouds
vec2 raymarch_clouds(vec3 dir, vec3 light_dir) {
    if(dir.y <= 0.0) return vec2(0.0);

    float density = 0.0;
    float light = 0.0;

    float cloud_height = 0.05;

    for(int i = 0; i < clouds_samples; i++) {
        float progress = float(i) / float(clouds_samples);
        vec3 sample_pos = dir * cloud_height * (progress + 0.3);

        float point_density = sample_cloud_density(sample_pos, progress);
        density += point_density;

        // Shadow sampling
        float shadow = 0.0;
        for(int s = 0; s < shadow_sample; s++) {
            float shadow_progress = float(s) / float(shadow_sample);
            vec3 shadow_offset = light_dir * cloud_height * shadow_progress * 0.5;
            shadow += sample_cloud_density(sample_pos + shadow_offset, progress);
        }
        light += shadow;
    }

    density = clamp(density / float(clouds_samples) * 3.0, 0.0, 1.0);
    light = light / float(shadow_sample * clouds_samples);

    return vec2(density, light);
}

void sky() {
    vec3 dir = EYEDIR;
    float horizon = abs(dir.y);

    // Sky gradient
    vec3 sky = mix(bottom_color, top_color, clamp(dir.y * 1.5, 0.0, 1.0));

    // Sun scatter at horizon
    sky += sun_scatter * pow(1.0 - horizon, 3.0) * 0.5;

    // Sun disc
    float sun_dist = distance(dir, LIGHT0_DIRECTION);
    float sun = smoothstep(sun_size, sun_size * 0.5, sun_dist);
    sky += sun_color * sun * sun_intensity;

    // Sun glow
    float glow = smoothstep(0.5, 0.0, sun_dist);
    sky += sun_color * glow * 0.3;

    // Stars
    if(stars_intensity > 0.0 && dir.y > 0.0) {
        vec2 stars = voronoi(dir * 30.0).xy;
        float twinkle = sin(TIME * 2.0 + stars.y * 10.0) * 0.5 + 0.5;
        float star = smoothstep(0.05, 0.0, stars.x) * twinkle;
        sky += star * stars_intensity * smoothstep(0.0, 0.3, dir.y);
    }

    // Cloud rendering
    if(AT_HALF_RES_PASS) {
        vec2 clouds = raymarch_clouds(vec3(dir.x, max(dir.y, 0.01), dir.z), LIGHT0_DIRECTION);
        vec3 cloud_color = mix(clouds_light_color * 0.6, clouds_light_color, exp(-clouds.y * clouds_shadow_intensity));
        COLOR = cloud_color;
        ALPHA = clouds.x * smoothstep(0.0, 0.1, dir.y);
    } else {
        COLOR = mix(sky, HALF_RES_COLOR.rgb, HALF_RES_COLOR.a);
    }
}
