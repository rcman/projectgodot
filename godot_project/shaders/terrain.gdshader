shader_type spatial;

uniform vec3 grass_color_1 : source_color = vec3(0.28, 0.52, 0.18);  // Vibrant green
uniform vec3 grass_color_2 : source_color = vec3(0.35, 0.58, 0.22);  // Lighter green
uniform vec3 grass_color_3 : source_color = vec3(0.22, 0.42, 0.15);  // Darker green
uniform vec3 dirt_color : source_color = vec3(0.45, 0.35, 0.25);

// Simple noise function
float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);

	float a = hash(i);
	float b = hash(i + vec2(1.0, 0.0));
	float c = hash(i + vec2(0.0, 1.0));
	float d = hash(i + vec2(1.0, 1.0));

	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
	float value = 0.0;
	float amplitude = 0.5;
	for (int i = 0; i < 4; i++) {
		value += amplitude * noise(p);
		p *= 2.0;
		amplitude *= 0.5;
	}
	return value;
}

void fragment() {
	vec2 uv = UV * 50.0;

	// Multiple layers of noise for natural grass variation
	float large_variation = fbm(uv * 0.1);
	float medium_variation = fbm(uv * 0.3);
	float small_variation = noise(uv);

	// Combine grass colors based on noise
	vec3 grass = mix(grass_color_1, grass_color_2, large_variation);
	grass = mix(grass, grass_color_3, medium_variation * 0.4);

	// Add subtle dirt patches
	float dirt_mask = smoothstep(0.65, 0.75, small_variation) * large_variation;
	vec3 color = mix(grass, dirt_color, dirt_mask * 0.3);

	// Slight brightness variation for depth
	color *= 0.9 + small_variation * 0.2;

	ALBEDO = color;
	ROUGHNESS = 0.85;
	SPECULAR = 0.1;
}
