shader_type sky;

// Real sky blue colors
uniform vec3 sky_blue : source_color = vec3(0.05, 0.35, 0.95);
uniform vec3 horizon_blue : source_color = vec3(0.4, 0.65, 0.95);
uniform vec3 sun_color : source_color = vec3(1.0, 0.98, 0.92);

// Cloud settings
uniform float cloud_coverage : hint_range(0.0, 1.0) = 0.5;
uniform float cloud_softness : hint_range(0.0, 1.0) = 0.3;

// Smooth noise
float hash(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

float smooth_noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * f * (f * (f * 6.0 - 15.0) + 10.0); // Quintic interpolation

    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));

    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float cloud_noise(vec2 p) {
    float value = 0.0;
    float amplitude = 0.6;
    float frequency = 1.0;

    // 6 octaves for soft, detailed clouds
    for (int i = 0; i < 6; i++) {
        value += amplitude * smooth_noise(p * frequency);
        frequency *= 2.0;
        amplitude *= 0.5;
    }
    return value;
}

void sky() {
    vec3 dir = EYEDIR;

    // Sky gradient - real blue sky colors
    float sky_gradient = clamp(dir.y, 0.0, 1.0);
    sky_gradient = pow(sky_gradient, 0.5); // More blue coverage
    vec3 sky = mix(horizon_blue, sky_blue, sky_gradient);

    // Atmospheric haze near horizon
    float haze = pow(1.0 - abs(dir.y), 6.0);
    sky = mix(sky, vec3(0.7, 0.85, 1.0), haze * 0.4);

    // Sun (fixed high position for noon)
    vec3 sun_dir = normalize(vec3(0.2, 0.85, 0.1));
    float sun_dot = dot(dir, sun_dir);

    // Sun glow
    float sun_glow = pow(max(0.0, sun_dot), 4.0) * 0.3;
    float sun_core = pow(max(0.0, sun_dot), 64.0) * 2.0;
    sky += sun_color * (sun_glow + sun_core);

    // Clouds - only in upper hemisphere
    if (dir.y > 0.02) {
        // Spherical projection for clouds (no cube artifacts)
        vec2 cloud_uv = dir.xz / max(dir.y, 0.1);
        cloud_uv *= 0.15; // Scale
        cloud_uv += TIME * 0.002; // Slow drift

        // Cloud density with soft edges
        float density = cloud_noise(cloud_uv);
        float threshold = 1.0 - cloud_coverage;
        float clouds = smoothstep(threshold - cloud_softness, threshold + cloud_softness, density);

        // Cloud shading - lighter tops, darker bottoms
        float cloud_detail = cloud_noise(cloud_uv * 3.0);
        float shading = 0.85 + 0.15 * cloud_detail;

        // Bright white clouds
        vec3 cloud_col = vec3(1.0, 1.0, 1.0) * shading;

        // Sun lighting on clouds
        cloud_col += sun_color * pow(max(0.0, sun_dot), 2.0) * 0.15;

        // Fade clouds at horizon
        float fade = smoothstep(0.02, 0.25, dir.y);
        clouds *= fade;

        sky = mix(sky, cloud_col, clouds * 0.95);
    }

    // Below horizon - ground color
    if (dir.y < 0.0) {
        float ground_grad = clamp(-dir.y, 0.0, 1.0);
        sky = mix(horizon_blue * 0.8, vec3(0.3, 0.35, 0.25), ground_grad);
    }

    COLOR = sky;
}
