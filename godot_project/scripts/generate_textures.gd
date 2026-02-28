@tool
extends EditorScript

## Generates placeholder PBR textures for terrain if real textures aren't available
## Run from Editor -> Run Script

const TEXTURE_SIZE = 512

func _run():
	print("Generating placeholder PBR textures...")

	var textures_dir = "res://textures/"
	DirAccess.make_dir_recursive_absolute(textures_dir)

	# Generate grass textures
	generate_grass_textures(textures_dir)

	# Generate dirt textures
	generate_dirt_textures(textures_dir)

	# Generate rock textures
	generate_rock_textures(textures_dir)

	# Generate snow textures
	generate_snow_textures(textures_dir)

	# Generate wind noise texture
	generate_noise_texture(textures_dir + "wind_noise.png", 256, 4.0)

	# Generate detail noise
	generate_noise_texture(textures_dir + "detail_noise.png", 256, 8.0)

	print("Done! Textures saved to res://textures/")

func generate_grass_textures(dir: String):
	# Albedo - green grass color with variation
	var albedo = Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_RGBA8)
	var normal = Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_RGBA8)
	var roughness = Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_L8)

	for y in TEXTURE_SIZE:
		for x in TEXTURE_SIZE:
			var noise = _fbm(x * 0.02, y * 0.02, 4) * 0.3
			var r = clamp(0.2 + noise * 0.15, 0.0, 1.0)
			var g = clamp(0.45 + noise * 0.2, 0.0, 1.0)
			var b = clamp(0.15 + noise * 0.1, 0.0, 1.0)
			albedo.set_pixel(x, y, Color(r, g, b, 1.0))

			# Normal map (mostly flat with slight variation)
			var nx = _fbm(x * 0.05, y * 0.05, 2) * 0.1
			var ny = _fbm(x * 0.05 + 100, y * 0.05, 2) * 0.1
			normal.set_pixel(x, y, Color(0.5 + nx, 0.5 + ny, 1.0, 1.0))

			# Roughness (grass is fairly rough)
			roughness.set_pixel(x, y, Color(0.7 + noise * 0.2, 0, 0))

	albedo.save_png(dir + "grass_albedo.png")
	normal.save_png(dir + "grass_normal.png")
	roughness.save_png(dir + "grass_roughness.png")
	print("  - Grass textures generated")

func generate_dirt_textures(dir: String):
	var albedo = Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_RGBA8)
	var normal = Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_RGBA8)
	var roughness = Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_L8)

	for y in TEXTURE_SIZE:
		for x in TEXTURE_SIZE:
			var noise = _fbm(x * 0.03, y * 0.03, 5) * 0.4
			var r = clamp(0.4 + noise * 0.2, 0.0, 1.0)
			var g = clamp(0.3 + noise * 0.15, 0.0, 1.0)
			var b = clamp(0.2 + noise * 0.1, 0.0, 1.0)
			albedo.set_pixel(x, y, Color(r, g, b, 1.0))

			var nx = _fbm(x * 0.08, y * 0.08, 3) * 0.2
			var ny = _fbm(x * 0.08 + 100, y * 0.08, 3) * 0.2
			normal.set_pixel(x, y, Color(0.5 + nx, 0.5 + ny, 1.0, 1.0))

			roughness.set_pixel(x, y, Color(0.85 + noise * 0.1, 0, 0))

	albedo.save_png(dir + "dirt_albedo.png")
	normal.save_png(dir + "dirt_normal.png")
	roughness.save_png(dir + "dirt_roughness.png")
	print("  - Dirt textures generated")

func generate_rock_textures(dir: String):
	var albedo = Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_RGBA8)
	var normal = Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_RGBA8)
	var roughness = Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_L8)

	for y in TEXTURE_SIZE:
		for x in TEXTURE_SIZE:
			var noise1 = _fbm(x * 0.02, y * 0.02, 6) * 0.5
			var noise2 = _fbm(x * 0.1, y * 0.1, 3) * 0.2
			var noise = noise1 + noise2
			var gray = clamp(0.45 + noise * 0.25, 0.0, 1.0)
			albedo.set_pixel(x, y, Color(gray * 0.95, gray * 0.92, gray * 0.88, 1.0))

			var nx = _fbm(x * 0.06, y * 0.06, 4) * 0.35
			var ny = _fbm(x * 0.06 + 100, y * 0.06, 4) * 0.35
			normal.set_pixel(x, y, Color(0.5 + nx, 0.5 + ny, 0.85, 1.0))

			roughness.set_pixel(x, y, Color(0.75 + noise * 0.15, 0, 0))

	albedo.save_png(dir + "rock_albedo.png")
	normal.save_png(dir + "rock_normal.png")
	roughness.save_png(dir + "rock_roughness.png")
	print("  - Rock textures generated")

func generate_snow_textures(dir: String):
	var albedo = Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_RGBA8)
	var normal = Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_RGBA8)
	var roughness = Image.create(TEXTURE_SIZE, TEXTURE_SIZE, false, Image.FORMAT_L8)

	for y in TEXTURE_SIZE:
		for x in TEXTURE_SIZE:
			var noise = _fbm(x * 0.015, y * 0.015, 4) * 0.15
			var white = clamp(0.92 + noise * 0.08, 0.0, 1.0)
			albedo.set_pixel(x, y, Color(white, white * 0.98, white * 1.02, 1.0))

			var nx = _fbm(x * 0.04, y * 0.04, 3) * 0.08
			var ny = _fbm(x * 0.04 + 100, y * 0.04, 3) * 0.08
			normal.set_pixel(x, y, Color(0.5 + nx, 0.5 + ny, 1.0, 1.0))

			# Snow is fairly smooth but not perfectly
			roughness.set_pixel(x, y, Color(0.5 + noise * 0.2, 0, 0))

	albedo.save_png(dir + "snow_albedo.png")
	normal.save_png(dir + "snow_normal.png")
	roughness.save_png(dir + "snow_roughness.png")
	print("  - Snow textures generated")

func generate_noise_texture(path: String, size: int, frequency: float):
	var img = Image.create(size, size, false, Image.FORMAT_L8)
	for y in size:
		for x in size:
			var value = _fbm(x * frequency / size, y * frequency / size, 4) * 0.5 + 0.5
			img.set_pixel(x, y, Color(value, value, value))
	img.save_png(path)

# Fractal Brownian Motion noise
func _fbm(x: float, y: float, octaves: int) -> float:
	var value = 0.0
	var amplitude = 1.0
	var frequency = 1.0
	var max_value = 0.0

	for i in octaves:
		value += _noise2d(x * frequency, y * frequency) * amplitude
		max_value += amplitude
		amplitude *= 0.5
		frequency *= 2.0

	return value / max_value

# Simple 2D noise (hash-based)
func _noise2d(x: float, y: float) -> float:
	var ix = int(floor(x))
	var iy = int(floor(y))
	var fx = x - floor(x)
	var fy = y - floor(y)

	# Smoothstep
	fx = fx * fx * (3.0 - 2.0 * fx)
	fy = fy * fy * (3.0 - 2.0 * fy)

	var a = _hash2d(ix, iy)
	var b = _hash2d(ix + 1, iy)
	var c = _hash2d(ix, iy + 1)
	var d = _hash2d(ix + 1, iy + 1)

	return lerp(lerp(a, b, fx), lerp(c, d, fx), fy) * 2.0 - 1.0

func _hash2d(x: int, y: int) -> float:
	var n = x + y * 57
	n = (n << 13) ^ n
	return (1.0 - float((n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff) / 1073741824.0)
