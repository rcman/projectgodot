extends CharacterBody3D

# Movement settings
@export var move_speed: float = 8.0
@export var sprint_speed: float = 14.0
@export var jump_velocity: float = 6.0
@export var mouse_sensitivity: float = 0.002
@export var gravity: float = 20.0

# Camera settings
@export var camera_smooth: float = 15.0
var camera_rotation := Vector2.ZERO
var target_camera_rotation := Vector2.ZERO

@onready var head: Node3D = $Head
@onready var camera: Camera3D = $Head/Camera3D

func _ready() -> void:
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

func _input(event: InputEvent) -> void:
	# Mouse look
	if event is InputEventMouseMotion and Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
		target_camera_rotation.x -= event.relative.y * mouse_sensitivity
		target_camera_rotation.y -= event.relative.x * mouse_sensitivity
		target_camera_rotation.x = clamp(target_camera_rotation.x, -PI/2.1, PI/2.1)

	# Toggle mouse capture
	if event.is_action_pressed("ui_cancel"):
		if Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
			Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
		else:
			Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

func _physics_process(delta: float) -> void:
	# Smooth camera rotation
	camera_rotation = camera_rotation.lerp(target_camera_rotation, camera_smooth * delta)
	head.rotation.x = camera_rotation.x
	rotation.y = camera_rotation.y

	# Gravity
	if not is_on_floor():
		velocity.y -= gravity * delta

	# Jump
	if Input.is_action_just_pressed("ui_accept") and is_on_floor():
		velocity.y = jump_velocity

	# Movement direction
	var input_dir := Vector2.ZERO
	if Input.is_key_pressed(KEY_W): input_dir.y -= 1
	if Input.is_key_pressed(KEY_S): input_dir.y += 1
	if Input.is_key_pressed(KEY_A): input_dir.x -= 1
	if Input.is_key_pressed(KEY_D): input_dir.x += 1
	input_dir = input_dir.normalized()

	# Calculate movement
	var direction := (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
	var current_speed := sprint_speed if Input.is_key_pressed(KEY_SHIFT) else move_speed

	if direction:
		velocity.x = direction.x * current_speed
		velocity.z = direction.z * current_speed
	else:
		velocity.x = move_toward(velocity.x, 0, current_speed * delta * 10)
		velocity.z = move_toward(velocity.z, 0, current_speed * delta * 10)

	move_and_slide()
