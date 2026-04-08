extends Node3D

@onready var debug_label: Label = $UI/DebugLabel

var _create_scene: PackedScene = preload("res://scenes/character_create.tscn")
var _create_ui: Control = null


func _ready() -> void:
	debug_label.text = "서버 연결 중..."

	GameServer.ws_connected.connect(_on_ws_connected)
	GameServer.ws_disconnected.connect(_on_ws_disconnected)
	GameServer.server_event_received.connect(_on_event)

	GameServer.get_status(_on_status_received)


func _on_status_received(code: int, data: Variant) -> void:
	if code == 200 and data is Dictionary:
		var count: int = data.get("characters", 0)
		debug_label.text = "서버 연결됨 — 캐릭터 %d명\n[C] 캐릭터 생성 | [L] 캐릭터 목록" % count
	else:
		debug_label.text = "서버 연결 실패\npython -m tomodachai.server 실행 필요"


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		match event.keycode:
			KEY_C:
				_toggle_create_ui()
			KEY_L:
				_list_characters()
			KEY_ESCAPE:
				_close_create_ui()


func _toggle_create_ui() -> void:
	if _create_ui != null:
		_close_create_ui()
		return
	_create_ui = _create_scene.instantiate()
	$UI.add_child(_create_ui)


func _close_create_ui() -> void:
	if _create_ui != null:
		_create_ui.queue_free()
		_create_ui = null
		# 캐릭터 수 갱신
		GameServer.get_status(_on_status_received)


func _list_characters() -> void:
	GameServer.get_characters(func(code: int, data: Variant) -> void:
		if code == 200 and data is Array:
			if data.is_empty():
				debug_label.text = "캐릭터 없음\n[C] 캐릭터 생성"
				return
			var lines: PackedStringArray = ["=== 캐릭터 목록 ==="]
			for c in data:
				var line := "ID:%d | %s | %s | %s" % [
					c.get("id", 0),
					c.get("name", "?"),
					c.get("personality_code", ""),
					c.get("zodiac", ""),
				]
				lines.append(line)
			lines.append("\n[C] 캐릭터 생성 | [L] 새로고침 | [ESC] 닫기")
			debug_label.text = "\n".join(lines)
		else:
			debug_label.text = "목록 조회 실패"
	)


func _on_ws_connected() -> void:
	pass


func _on_ws_disconnected() -> void:
	debug_label.text = "WebSocket 끊김 — 재연결 중..."


func _on_event(event: Dictionary) -> void:
	var summary: String = event.get("summary", event.get("type", "???"))
	debug_label.text = "이벤트: %s\n\n[C] 캐릭터 생성 | [L] 목록" % summary
