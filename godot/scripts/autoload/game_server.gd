extends Node

## FastAPI 서버와의 통신을 관리하는 오토로드 싱글톤.

const BASE_URL: String = "http://127.0.0.1:8000/api"

var _ws: WebSocketPeer = null
var _ws_connected: bool = false

signal server_event_received(event: Dictionary)
signal ws_connected()
signal ws_disconnected()

# 콜백 대기열: {HTTPRequest: Callable}
var _pending: Dictionary = {}


func _ready() -> void:
	_connect_websocket()


# ---------------------------------------------------------------------------
# REST
# ---------------------------------------------------------------------------

func _do_request(method: int, endpoint: String, body: String, callback: Callable) -> void:
	var http := HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_request_done.bind(http, callback))
	var headers: PackedStringArray = ["Content-Type: application/json"]
	var err := http.request(BASE_URL + endpoint, headers, method, body)
	if err != OK:
		push_warning("HTTP request failed: %s" % error_string(err))
		http.queue_free()


func _on_request_done(p_result: int, p_code: int, p_headers: PackedStringArray, p_body: PackedByteArray, http: HTTPRequest, callback: Callable) -> void:
	var json_str := p_body.get_string_from_utf8()
	var json := JSON.new()
	var parsed: Variant = null
	if json.parse(json_str) == OK:
		parsed = json.data
	http.queue_free()
	if callback.is_valid():
		callback.call(p_code, parsed)


# --- Public API ---

func get_status(callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_GET, "/status", "", callback)


func get_game(callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_GET, "/game", "", callback)


func get_characters(callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_GET, "/characters", "", callback)


func get_character(char_id: int, callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_GET, "/characters/%d" % char_id, "", callback)


func create_character(data: Dictionary, callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_POST, "/characters", JSON.stringify(data), callback)


func get_relationships(callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_GET, "/relationships", "", callback)


func get_locations(callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_GET, "/locations", "", callback)


func do_tick(callback: Callable, seed: int = -1) -> void:
	var body := "{}"
	if seed >= 0:
		body = JSON.stringify({"seed": seed})
	_do_request(HTTPClient.METHOD_POST, "/tick", body, callback)


func do_connect(callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_POST, "/connect", "", callback)


func get_time(callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_GET, "/time", "", callback)


func save_game(slot: int, callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_POST, "/save/%d" % slot, "", callback)


func load_game(slot: int, callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_POST, "/load/%d" % slot, "", callback)


func get_saves(callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_GET, "/saves", "", callback)


func move_character(char_id: int, destination: String, callback: Callable) -> void:
	_do_request(HTTPClient.METHOD_POST, "/locations/move/%d/%s" % [char_id, destination], "", callback)


func generate_name(gender: String, callback: Callable) -> void:
	var endpoint := "/characters/generate-name"
	if not gender.is_empty():
		endpoint += "?gender=%s" % gender
	_do_request(HTTPClient.METHOD_GET, endpoint, "", callback)


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

func _connect_websocket() -> void:
	_ws = WebSocketPeer.new()
	var url := BASE_URL.replace("http://", "ws://") + "/ws"
	var err := _ws.connect_to_url(url)
	if err != OK:
		push_warning("WebSocket connection failed: %s" % error_string(err))
		_ws = null


func _process(_delta: float) -> void:
	if _ws == null:
		return
	_ws.poll()

	var state := _ws.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN:
		if not _ws_connected:
			_ws_connected = true
			ws_connected.emit()
		while _ws.get_available_packet_count() > 0:
			var packet := _ws.get_packet().get_string_from_utf8()
			var json := JSON.new()
			if json.parse(packet) == OK:
				var data: Variant = json.data
				if data is Dictionary and data.has("events"):
					for event in data["events"]:
						server_event_received.emit(event)
	elif state == WebSocketPeer.STATE_CLOSED:
		if _ws_connected:
			_ws_connected = false
			ws_disconnected.emit()
		_ws = null
		# 3초 후 재연결
		await get_tree().create_timer(3.0).timeout
		_connect_websocket()
