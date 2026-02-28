extends Node3D

@export var day_duration: float = 120.0  # Seconds per full day cycle
@export var time_scale: float = 1.0  # Speed multiplier

@onready var sun: DirectionalLight3D = $"../Sun"
@onready var world_env: WorldEnvironment = $"../WorldEnvironment"

var time_of_day: float = 0.3  # Start at morning (0-1 range, 0.5 = noon)

# Sky colors for different times
const DAWN_SKY = Color(0.9, 0.5, 0.3)
const DAY_SKY = Color(0.35, 0.55, 0.85)
const DUSK_SKY = Color(0.9, 0.4, 0.2)
const NIGHT_SKY = Color(0.05, 0.05, 0.15)

const DAWN_HORIZON = Color(0.95, 0.7, 0.4)
const DAY_HORIZON = Color(0.7, 0.8, 0.9)
const DUSK_HORIZON = Color(0.95, 0.5, 0.3)
const NIGHT_HORIZON = Color(0.1, 0.1, 0.2)

func _ready() -> void:
	update_cycle(time_of_day)

func _process(delta: float) -> void:
	time_of_day += (delta * time_scale) / day_duration
	time_of_day = fmod(time_of_day, 1.0)
	update_cycle(time_of_day)

func update_cycle(t: float) -> void:
	if not sun or not world_env:
		return

	# Sun rotation (full 360 degrees over the day)
	var sun_angle = t * TAU - PI / 2  # Start at horizon
	sun.rotation.x = sun_angle
	sun.rotation.y = -0.5  # Slight angle for interesting shadows

	# Sun intensity based on height
	var sun_height = sin(sun_angle)
	var intensity = clamp(sun_height * 2.0, 0.0, 1.2)
	sun.light_energy = intensity
	sun.shadow_enabled = sun_height > 0.0

	# Sun color - warmer at dawn/dusk
	var sun_color = Color.WHITE
	if sun_height < 0.3 and sun_height > -0.1:
		sun_color = Color(1.0, 0.8, 0.6)  # Warm orange
	sun.light_color = sun_color

	# Update sky colors
	var env = world_env.environment
	if env and env.sky and env.sky.sky_material:
		var sky_mat = env.sky.sky_material as ProceduralSkyMaterial
		if sky_mat:
			var sky_color: Color
			var horizon_color: Color

			if t < 0.25:  # Night to dawn
				var blend = t / 0.25
				sky_color = NIGHT_SKY.lerp(DAWN_SKY, blend)
				horizon_color = NIGHT_HORIZON.lerp(DAWN_HORIZON, blend)
			elif t < 0.35:  # Dawn to day
				var blend = (t - 0.25) / 0.1
				sky_color = DAWN_SKY.lerp(DAY_SKY, blend)
				horizon_color = DAWN_HORIZON.lerp(DAY_HORIZON, blend)
			elif t < 0.65:  # Day
				sky_color = DAY_SKY
				horizon_color = DAY_HORIZON
			elif t < 0.75:  # Day to dusk
				var blend = (t - 0.65) / 0.1
				sky_color = DAY_SKY.lerp(DUSK_SKY, blend)
				horizon_color = DAY_HORIZON.lerp(DUSK_HORIZON, blend)
			elif t < 0.85:  # Dusk to night
				var blend = (t - 0.75) / 0.1
				sky_color = DUSK_SKY.lerp(NIGHT_SKY, blend)
				horizon_color = DUSK_HORIZON.lerp(NIGHT_HORIZON, blend)
			else:  # Night
				sky_color = NIGHT_SKY
				horizon_color = NIGHT_HORIZON

			sky_mat.sky_top_color = sky_color
			sky_mat.sky_horizon_color = horizon_color

		# Ambient light
		env.ambient_light_energy = clamp(sun_height + 0.3, 0.1, 0.6)
