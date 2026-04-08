extends Control

## 캐릭터 생성 위저드 — 4단계
## Step 1: 외형 (미구현 → 플레이스홀더)
## Step 2: 프로필 (이름, 생일, 혈액형, 성별, 좋아하는 색)
## Step 3: 목소리 (미구현 → 플레이스홀더)
## Step 4: 성격 (슬라이더 5개)

signal character_created(char_id: int)

## 16가지 성격 유형 (영문 키 기준, 01-character.md)
## easygoing(안정파): 외유내강/다정다감/우유부단/순진무구
## outgoing(사교파): 좌충우돌/시끌벅적/재기발랄/명랑쾌활
## confident(주도파): 시원시원/속전속결/유아독존/거두절미
## independent(신중파): 완전무결/유비무환/우물쭈물/묵묵부답

## 계통 코드 → 한글 표시명 (01-character.md 기준)
const GROUP_LABELS: Dictionary = {
	"easygoing": "안정파",
	"outgoing": "사교파",
	"confident": "주도파",
	"independent": "신중파",
}

const COLORS: Array[String] = [
	"빨간색", "주황색", "노란색", "초록색", "파란색",
	"남색", "보라색", "분홍색", "하얀색", "검은색",
	"하늘색", "연두색", "형광 노란색", "라벤더",
]


var _step: int = 0  # 0~3
var _next_id: int = 1
var _char_data: Dictionary = {}

# UI 노드들 — _ready에서 동적 생성
var _title_label: Label
var _content: VBoxContainer
var _prev_btn: Button
var _next_btn: Button
var _random_btn: Button
var _result_label: Label

# Step 2 inputs
var _name_input: LineEdit
var _birthday_m: SpinBox
var _birthday_d: SpinBox
var _blood_select: OptionButton
var _gender_select: OptionButton
var _color_select: OptionButton

# Step 4 sliders
var _slider_movement: HSlider
var _slider_speech: HSlider
var _slider_express: HSlider
var _slider_attitude: HSlider
var _slider_overall: HSlider
var _personality_label: Label


func _ready() -> void:
	_build_ui()
	_show_step(0)

	GameServer.get_characters(func(code: int, data: Variant) -> void:
		if code == 200 and data is Array:
			_next_id = data.size() + 1
	)


# ---------------------------------------------------------------------------
# UI 빌드
# ---------------------------------------------------------------------------

func _build_ui() -> void:
	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.offset_left = -280.0
	panel.offset_top = -300.0
	panel.offset_right = 280.0
	panel.offset_bottom = 300.0
	add_child(panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 20)
	margin.add_theme_constant_override("margin_top", 15)
	margin.add_theme_constant_override("margin_right", 20)
	margin.add_theme_constant_override("margin_bottom", 15)
	panel.add_child(margin)

	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 6)
	margin.add_child(root)

	# 타이틀
	_title_label = Label.new()
	_title_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root.add_child(_title_label)

	root.add_child(HSeparator.new())

	# 컨텐츠 영역
	_content = VBoxContainer.new()
	_content.add_theme_constant_override("separation", 5)
	_content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(_content)

	# 결과 라벨
	_result_label = Label.new()
	_result_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_result_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	root.add_child(_result_label)

	root.add_child(HSeparator.new())

	# 버튼 행
	var btn_row := HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 10)
	btn_row.alignment = BoxContainer.ALIGNMENT_CENTER
	root.add_child(btn_row)

	_prev_btn = Button.new()
	_prev_btn.text = "이전"
	_prev_btn.pressed.connect(_on_prev)
	btn_row.add_child(_prev_btn)

	_random_btn = Button.new()
	_random_btn.text = "랜덤"
	_random_btn.pressed.connect(_on_random)
	btn_row.add_child(_random_btn)

	_next_btn = Button.new()
	_next_btn.text = "다음"
	_next_btn.pressed.connect(_on_next)
	btn_row.add_child(_next_btn)


# ---------------------------------------------------------------------------
# 스텝 전환
# ---------------------------------------------------------------------------

func _show_step(step: int) -> void:
	_step = step
	_clear_content()
	_result_label.text = ""

	match step:
		0: _build_step_appearance()
		1: _build_step_profile()
		2: _build_step_voice()
		3: _build_step_personality()

	_prev_btn.visible = step > 0
	_next_btn.text = "입주시키기" if step == 3 else "다음"


func _clear_content() -> void:
	for child in _content.get_children():
		child.queue_free()


func _add_label(text: String) -> Label:
	var l := Label.new()
	l.text = text
	_content.add_child(l)
	return l


# ---------------------------------------------------------------------------
# Step 0: 외형
# ---------------------------------------------------------------------------

func _build_step_appearance() -> void:
	_title_label.text = "1/4 — 외형"
	_add_label("(3D 모델링 준비 중)")
	_add_label("")
	_add_label("외형 커스터마이징은 추후 구현됩니다.")
	_add_label("지금은 기본 외형으로 진행합니다.")


# ---------------------------------------------------------------------------
# Step 1: 프로필
# ---------------------------------------------------------------------------

func _build_step_profile() -> void:
	_title_label.text = "2/4 — 프로필"

	_add_label("이름")
	_name_input = LineEdit.new()
	_content.add_child(_name_input)

	_add_label("생일")
	var bday_row := HBoxContainer.new()
	bday_row.add_theme_constant_override("separation", 5)
	_content.add_child(bday_row)

	_birthday_m = SpinBox.new()
	_birthday_m.min_value = 1
	_birthday_m.max_value = 12
	_birthday_m.value = 1
	_birthday_m.prefix = ""
	_birthday_m.suffix = "월"
	bday_row.add_child(_birthday_m)

	_birthday_d = SpinBox.new()
	_birthday_d.min_value = 1
	_birthday_d.max_value = 31
	_birthday_d.value = 1
	_birthday_d.prefix = ""
	_birthday_d.suffix = "일"
	bday_row.add_child(_birthday_d)

	_add_label("혈액형")
	_blood_select = OptionButton.new()
	_blood_select.add_item("A")
	_blood_select.add_item("B")
	_blood_select.add_item("O")
	_blood_select.add_item("AB")
	_blood_select.selected = 0
	_content.add_child(_blood_select)

	_add_label("성별")
	_gender_select = OptionButton.new()
	_gender_select.add_item("남")
	_gender_select.add_item("여")
	_gender_select.selected = 0
	_content.add_child(_gender_select)

	_add_label("좋아하는 색")
	_color_select = OptionButton.new()
	for c in COLORS:
		_color_select.add_item(c)
	_color_select.selected = 0
	_content.add_child(_color_select)

	# 이전 데이터 복원
	if _char_data.has("name"):
		_name_input.text = _char_data["name"]


# ---------------------------------------------------------------------------
# Step 2: 목소리
# ---------------------------------------------------------------------------

func _build_step_voice() -> void:
	_title_label.text = "3/4 — 목소리"
	_add_label("(TTS 시스템 준비 중)")
	_add_label("")
	_add_label("목소리 설정은 추후 구현됩니다.")
	_add_label("지금은 기본 목소리로 진행합니다.")


# ---------------------------------------------------------------------------
# Step 3: 성격
# ---------------------------------------------------------------------------

func _build_step_personality() -> void:
	_title_label.text = "4/4 — 성격"

	_slider_movement = _add_slider("움직임 (느림 ↔ 빠름)")
	_slider_speech = _add_slider("말투 (유순 ↔ 직설)")
	_slider_express = _add_slider("표현력 (냉정 ↔ 감정적)")
	_slider_attitude = _add_slider("태도 (진지 ↔ 여유)")
	_slider_overall = _add_slider("전체 (독특 ↔ 평범)")

	_personality_label = Label.new()
	_personality_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_content.add_child(_personality_label)

	# 슬라이더 변경 시 성격 유형 실시간 표시
	_slider_movement.value_changed.connect(func(_v: float) -> void: _update_personality_preview())
	_slider_speech.value_changed.connect(func(_v: float) -> void: _update_personality_preview())
	_slider_express.value_changed.connect(func(_v: float) -> void: _update_personality_preview())
	_slider_attitude.value_changed.connect(func(_v: float) -> void: _update_personality_preview())

	# 이전 데이터 복원
	if _char_data.has("movement"):
		_slider_movement.value = _char_data["movement"]
		_slider_speech.value = _char_data["speech"]
		_slider_express.value = _char_data["expressiveness"]
		_slider_attitude.value = _char_data["attitude"]
		_slider_overall.value = _char_data["overall"]

	_update_personality_preview()


func _add_slider(label_text: String) -> HSlider:
	_add_label(label_text)
	var slider := HSlider.new()
	slider.min_value = 0
	slider.max_value = 10
	slider.step = 1
	slider.value = 5
	_content.add_child(slider)
	return slider


func _update_personality_preview() -> void:
	if _personality_label == null:
		return
	var group := _get_personality_group()
	var label: String = GROUP_LABELS.get(group, group)
	var type_name := _get_type_label(group)
	_personality_label.text = "→ %s — %s" % [label, type_name]


func _get_personality_group() -> String:
	var ms := (_slider_movement.value + _slider_speech.value) / 20.0
	if ms < 0.25:
		return "easygoing"
	elif ms < 0.5:
		return "independent"
	elif ms < 0.75:
		return "confident"
	else:
		return "outgoing"


func _get_type_index() -> int:
	var ea := (_slider_express.value + _slider_attitude.value) / 20.0
	if ea < 0.25:
		return 0
	elif ea < 0.5:
		return 1
	elif ea < 0.75:
		return 2
	else:
		return 3


func _get_type_label(group: String) -> String:
	var labels: Dictionary = {
		"easygoing": ["외유내강형", "다정다감형", "우유부단형", "순진무구형"],
		"outgoing": ["좌충우돌형", "시끌벅적형", "재기발랄형", "명랑쾌활형"],
		"confident": ["시원시원형", "속전속결형", "유아독존형", "거두절미형"],
		"independent": ["완전무결형", "유비무환형", "우물쭈물형", "묵묵부답형"],
	}
	var idx := _get_type_index()
	if labels.has(group):
		return labels[group][idx]
	return "?"


# ---------------------------------------------------------------------------
# 버튼 핸들러
# ---------------------------------------------------------------------------

func _on_prev() -> void:
	_save_current_step()
	_show_step(_step - 1)


func _on_next() -> void:
	_save_current_step()

	if _step < 3:
		# 프로필 단계 검증
		if _step == 1:
			if _char_data.get("name", "").is_empty():
				_result_label.text = "이름을 입력해주세요."
				return
		_show_step(_step + 1)
	else:
		_submit()


func _on_random() -> void:
	match _step:
		1: _randomize_profile()
		3: _randomize_personality()


func _save_current_step() -> void:
	match _step:
		1:
			if _name_input:
				_char_data["name"] = _name_input.text.strip_edges()
				_char_data["birthday"] = "%02d-%02d" % [int(_birthday_m.value), int(_birthday_d.value)]
				_char_data["blood_type"] = _blood_select.get_item_text(_blood_select.selected)
				_char_data["gender"] = _gender_select.get_item_text(_gender_select.selected)
				_char_data["favorite_color"] = _color_select.get_item_text(_color_select.selected)
		3:
			if _slider_movement:
				_char_data["movement"] = int(_slider_movement.value)
				_char_data["speech"] = int(_slider_speech.value)
				_char_data["expressiveness"] = int(_slider_express.value)
				_char_data["attitude"] = int(_slider_attitude.value)
				_char_data["overall"] = int(_slider_overall.value)


func _randomize_profile() -> void:
	# 이름은 건드리지 않음 — 직접 입력
	_gender_select.selected = randi() % 2
	_birthday_m.value = randi_range(1, 12)
	_birthday_d.value = randi_range(1, 28)
	_blood_select.selected = randi() % 4
	_color_select.selected = randi() % COLORS.size()


func _randomize_personality() -> void:
	_slider_movement.value = randi_range(0, 10)
	_slider_speech.value = randi_range(0, 10)
	_slider_express.value = randi_range(0, 10)
	_slider_attitude.value = randi_range(0, 10)
	_slider_overall.value = randi_range(0, 10)
	_update_personality_preview()


# ---------------------------------------------------------------------------
# 제출
# ---------------------------------------------------------------------------

func _submit() -> void:
	_save_current_step()

	var api_data := {
		"id": _next_id,
		"name": _char_data.get("name", ""),
		"birthday": _char_data.get("birthday", ""),
		"blood_type": _char_data.get("blood_type", "A"),
		"gender": _char_data.get("gender", "남"),
		"favorite_color": _char_data.get("favorite_color", ""),
		"personality_code": _determine_personality_code(),
		"personality": {
			"movement": _char_data.get("movement", 5),
			"speech": _char_data.get("speech", 5),
			"expressiveness": _char_data.get("expressiveness", 5),
			"attitude": _char_data.get("attitude", 5),
			"overall": _char_data.get("overall", 5),
		},
	}

	_next_btn.disabled = true
	_result_label.text = "입주 처리 중..."

	GameServer.create_character(api_data, _on_created)


func _on_created(code: int, data: Variant) -> void:
	_next_btn.disabled = false

	if code == 201 and data is Dictionary:
		var cid: int = data.get("id", -1)
		var cname: String = data.get("name", "?")
		_result_label.text = "%s (ID:%d) 입주 완료!" % [cname, cid]
		_next_id += 1
		character_created.emit(cid)
	elif code == 409:
		_result_label.text = "중복 ID — 다시 시도해주세요."
		_next_id += 1
	else:
		_result_label.text = "실패 (코드: %d)" % code


func _determine_personality_code() -> String:
	var group := _get_personality_group()
	var idx := _get_type_index()

	var type_map: Dictionary = {
		"easygoing": ["easygoing_softie", "easygoing_optimist", "easygoing_carer", "easygoing_dreamer"],
		"independent": ["independent_dogooder", "independent_perfectionist", "independent_introvert", "independent_thinker"],
		"confident": ["confident_busybee", "confident_gogetter", "confident_freespirit", "confident_brainiac"],
		"outgoing": ["outgoing_charmer", "outgoing_dynamo", "outgoing_buddy", "outgoing_extrovert"],
	}

	return type_map[group][idx]
