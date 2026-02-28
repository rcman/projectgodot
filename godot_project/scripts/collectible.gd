extends Area3D

signal collected

@export var rotation_speed: float = 2.0
@export var bob_speed: float = 2.0
@export var bob_height: float = 0.2

var initial_y: float
var time_offset: float

func _ready() -> void:
	initial_y = position.y
	time_offset = randf() * TAU
	body_entered.connect(_on_body_entered)

func _process(delta: float) -> void:
	# Rotate
	rotate_y(rotation_speed * delta)

	# Bob up and down
	position.y = initial_y + sin(Time.get_ticks_msec() * 0.001 * bob_speed + time_offset) * bob_height

func _on_body_entered(body: Node3D) -> void:
	if body.is_in_group("player") or body.name == "Player":
		collected.emit()
		# Simple collection effect
		var tween = create_tween()
		tween.tween_property(self, "scale", Vector3.ZERO, 0.2)
		tween.tween_callback(queue_free)
