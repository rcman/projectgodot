extends CanvasLayer

var collectibles_found: int = 0
var total_collectibles: int = 0

@onready var compass_needle: TextureRect = $Compass/Needle
@onready var collectible_label: Label = $CollectibleCounter
@onready var crosshair: Control = $Crosshair

func _ready() -> void:
	# Count total collectibles in scene
	total_collectibles = get_tree().get_nodes_in_group("collectibles").size()
	if total_collectibles == 0:
		# Fallback: count Area3D nodes named Collectible_*
		for node in get_tree().root.get_children():
			_count_collectibles(node)

	update_counter()

	# Connect to all collectibles
	for node in get_tree().root.get_children():
		_connect_collectibles(node)

func _count_collectibles(node: Node) -> void:
	if node.name.begins_with("Collectible_"):
		total_collectibles += 1
	for child in node.get_children():
		_count_collectibles(child)

func _connect_collectibles(node: Node) -> void:
	if node.name.begins_with("Collectible_") and node.has_signal("collected"):
		node.collected.connect(_on_collectible_collected)
	for child in node.get_children():
		_connect_collectibles(child)

func _process(_delta: float) -> void:
	update_compass()

func update_compass() -> void:
	if not compass_needle:
		return

	# Get player camera direction
	var camera = get_viewport().get_camera_3d()
	if camera:
		var forward = -camera.global_transform.basis.z
		var angle = atan2(forward.x, forward.z)
		compass_needle.rotation = -angle

func _on_collectible_collected() -> void:
	collectibles_found += 1
	update_counter()

func update_counter() -> void:
	if collectible_label:
		collectible_label.text = "Gems: %d / %d" % [collectibles_found, total_collectibles]
