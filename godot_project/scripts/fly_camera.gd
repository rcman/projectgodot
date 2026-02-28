extends Camera3D

@export var move_speed: float = 10.0
@export var look_sensitivity: float = 0.002
@export var fast_multiplier: float = 3.0

var velocity := Vector3.ZERO
var mouse_captured := false

func _ready():
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	mouse_captured = true

func _input(event):
	if event is InputEventMouseMotion and mouse_captured:
		rotate_y(-event.relative.x * look_sensitivity)
		rotate_object_local(Vector3.RIGHT, -event.relative.y * look_sensitivity)

	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_ESCAPE:
			if mouse_captured:
				Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
				mouse_captured = false
			else:
				get_tree().quit()
		elif event.keycode == KEY_TAB:
			mouse_captured = !mouse_captured
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if mouse_captured else Input.MOUSE_MODE_VISIBLE

func _physics_process(delta):
	var input_dir := Vector3.ZERO

	if Input.is_key_pressed(KEY_W):
		input_dir -= transform.basis.z
	if Input.is_key_pressed(KEY_S):
		input_dir += transform.basis.z
	if Input.is_key_pressed(KEY_A):
		input_dir -= transform.basis.x
	if Input.is_key_pressed(KEY_D):
		input_dir += transform.basis.x
	if Input.is_key_pressed(KEY_SPACE):
		input_dir += Vector3.UP
	if Input.is_key_pressed(KEY_CTRL):
		input_dir += Vector3.DOWN

	var speed = move_speed
	if Input.is_key_pressed(KEY_SHIFT):
		speed *= fast_multiplier

	if input_dir.length() > 0:
		input_dir = input_dir.normalized()

	position += input_dir * speed * delta
