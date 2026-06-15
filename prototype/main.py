#!/usr/bin/env python3
# AI 토모다치 라이프 — 터미널 프로토타입
# 그래픽 없이 텍스트만으로 핵심 루프(관찰 → 이벤트 → 개입)를 검증한다.
# LLM은 임시로 Codex CLI(codex exec)를 사용. --mock 으로 LLM 없이도 실행 가능.
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import threading
import time
from collections import Counter

from game import items, relationship
from game.llm import make_provider
from game.models import Character, GameState
from game.personality import personality_label, classify
from game.save import load_game, save_game
from game.simulation import LOCATIONS, Simulation, TickResult

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HELP = """\
명령어:
  (엔터) 또는 s [n]   시간 진행 (n틱, 1틱 = 게임 내 30분)
  auto [초]           자동 진행 켜기/속도 변경 (기본 3초/틱).
                      백그라운드로 시간이 흐르며 이벤트가 올라오고, 그동안에도 명령 입력 가능.
                      고백 말풍선·싸움·이별 같은 큰 이벤트가 일어나면 자동으로 멈춤
  pause               자동 진행 끄기 (auto off 도 동일)
  status [이름]       마을 전체 / 캐릭터 상세 상태
  rel                 마을 전체 관계도 요약 (연인/베프/원수, 반함·연애 기류, 전 연인 이력)
  rel <이름>          해당 캐릭터의 관계 보기 (수치는 비공개, 상태 텍스트만)
  map                 누가 어디에 있는지 보기
  bubbles             대기 중 말풍선 확인/응답 (고백 허락 등)
  feed <이름> [음식]  음식 주기 (음식 생략 시 목록 표시)
  feed all [음식]     전원에게 음식 주기 (디버그용. 음식 생략 시 각자 무난한 걸로)
  dex <이름>          음식 도감 (줘본 것만 표시)
  give <이름> <도구>  도구 주기 (카메라=사진 촬영, 프라이팬=즉흥 요리)
  album               마을 기록 (사진 갤러리 + 요리 카탈로그)
  log [n]             최근 이벤트 로그 n건 (기본 10)
  news [weird]        뉴스 브리핑 (weird: 병맛 뉴스)
  save / load         수동 저장 / 불러오기 (10틱마다 + 종료 시 자동 저장도 됨)
  help                이 도움말
  quit                종료
"""


def build_new_game(chars_path: str, seed: int) -> GameState:
    # 초기 캐릭터 로드 + 음식 선호 순위 랜덤 확정 (생성 시 확정, 불변)
    rng = random.Random(seed)
    state = GameState()
    state.rng = rng
    with open(chars_path, encoding="utf-8") as f:
        defs = json.load(f)
    for i, d in enumerate(defs, start=1):
        ranks = list(range(len(items.FOODS)))
        rng.shuffle(ranks)
        char = Character(
            id=i, name=d["name"], gender=d["gender"],
            birthday=d["birthday"], blood_type=d["blood_type"],
            **d["personality"],
            speech_habits=d.get("speech_habits", {}),
            mini_traits={k: v for k, v in d.get("mini_traits", {}).items() if v},
            food_ranks=ranks,
            food_eaten=[False] * len(items.FOODS),
            seed=rng.randrange(10 ** 6),
            location=rng.choice(list(LOCATIONS.keys())),
        )
        state.characters[char.id] = char
    state.announcer = rng.choice(list(state.characters.keys()))
    return state


def print_result(result: TickResult) -> None:
    if result.scene:
        print(f"\n{result.scene}")
    for speaker, text in result.dialogue:
        print(f"   {speaker}: “{text}”")
    for msg in result.messages:
        print(f" {msg}")


def find_char(state: GameState, name: str):
    for c in state.characters.values():
        if c.name == name:
            return c
    print(f" ❓ '{name}' 라는 주민이 없습니다. (주민: {', '.join(c.name for c in state.characters.values())})")
    return None


def cmd_status(state: GameState, name: str = "") -> None:
    if not name:
        print(f"\n🏘 {state.village_name} — Day {state.day} {state.clock()}")
        for c in state.characters.values():
            group, form = classify(c)
            flags = []
            if c.despair:
                flags.append("👻절망")
            if c.hunger >= 80:
                flags.append("🍚배고픔")
            print(f"  {c.name} ({'남' if c.gender == 'M' else '여'}, {group} {form})"
                  f" — 기분: {c.mood.label()}, Lv.{c.level}"
                  + (" " + " ".join(flags) if flags else ""))
        return
    c = find_char(state, name)
    if not c:
        return
    print(f"\n👤 {c.name} — {personality_label(c)}")
    print(f"  혈액형 {c.blood_type} / 생일 {c.birthday} / 위치: {LOCATIONS[c.location][0]}")
    print(f"  기분: {c.mood.label()} / {('배고픔!' if c.hunger >= 80 else '포만감 보통' if c.hunger >= 40 else '배부름')}"
          f" / 만족도 {'😊 높음' if c.satisfaction >= 50 else '😐 보통' if c.satisfaction >= 0 else '👻 절망!'}")
    habits = c.speech_habits.get("normal", "")
    if habits:
        print(f"  말버릇: \"{habits}\"")
    slots = []
    for key, label in (("best_friend", "베프"), ("lover", "연인"), ("enemy", "원수")):
        if c.slots.get(key) is not None:
            slots.append(f"{label}: {state.characters[c.slots[key]].name}")
    if slots:
        print("  " + " / ".join(slots))


def cmd_relmap(state: GameState) -> None:
    # 시청 '관계도 그래프 (전체 보기)'의 텍스트 축약판: 주요 관계만 엣지로 표시
    chars = list(state.characters.values())
    slots, flows, crushes, history = [], [], [], []

    for a in chars:
        for b in chars:
            if a.id >= b.id:
                continue
            ra = a.relationships.get(b.id)
            rb = b.relationships.get(a.id)
            if ra is None or rb is None:
                continue
            # 지정 관계 슬롯
            if a.slots["lover"] == b.id:
                slots.append(f"  ♥ {a.name} ↔ {b.name} : 연인")
            elif a.slots["best_friend"] == b.id:
                slots.append(f"  💛 {a.name} ↔ {b.name} : 베프")
            elif a.slots["enemy"] == b.id:
                slots.append(f"  ⚡ {a.name} ↔ {b.name} : 원수")
            else:
                # 슬롯 외의 흐름 (양방향 수치 중 낮은 쪽 기준)
                mf = min(ra.friendship, rb.friendship)
                if mf >= 40:
                    flows.append(f"  🤝 {a.name} ↔ {b.name} : {relationship.friendship_label(mf)}")
                elif mf <= -20:
                    flows.append(f"  💢 {a.name} ↔ {b.name} : {relationship.friendship_label(mf)}")
            # 전 연인 태그 (슬롯과 독립)
            for tag in a.ex_lovers:
                if tag.target == b.id:
                    history.append(f"  ↯ {a.name} ↔ {b.name} : 전 연인"
                                   f" (사유: {relationship.BREAKUP_REASONS[tag.reason]}, day {tag.day})")

    # 짝사랑/연애 기류 (방향성). 깊어지기 전의 반함도 💘로 표시
    for a in chars:
        for b_id, r in a.relationships.items():
            if a.slots["lover"] == b_id:
                continue
            label = relationship.romance_label(r.romance)
            if label and r.romance >= 21:
                crushes.append(f"  💗 {a.name} → {state.characters[b_id].name} : {label}")
            elif r.spark:
                crushes.append(f"  💘 {a.name} → {state.characters[b_id].name} : 반했음")

    print(f"\n🏛 {state.village_name} 관계도 요약 (Day {state.day})")
    for title, lines in (("지정 관계", slots), ("가까워지는 사이", flows),
                         ("연애 기류", crushes), ("관계 이력", history)):
        if lines:
            print(f" [{title}]")
            for l in lines:
                print(l)
    if not (slots or flows or crushes or history):
        # 아직 큰 관계가 없는 초반에는 최근 자주 만난 짝이라도 보여줌
        recent = [e for e in state.events
                  if e.type == "conversation" and e.day >= state.day - 1
                  and len(e.participants) >= 2]
        pair_counts = Counter(tuple(sorted(e.participants[:2])) for e in recent)
        if pair_counts:
            print("  아직 뚜렷한 관계는 없지만, 요즘 자주 어울리는 사이가 보이네요:")
            for (x, y), n in pair_counts.most_common(3):
                print(f"  👋 {state.characters[x].name} ↔ {state.characters[y].name}"
                      f" : 최근 대화 {n}번")
        else:
            print("  아직 눈에 띄는 관계가 없습니다. 다들 서로 알아가는 중이에요.")


def cmd_rel(state: GameState, name: str) -> None:
    c = find_char(state, name)
    if not c:
        return
    print(f"\n💞 {c.name}의 관계:")
    if not c.relationships:
        print("  아직 아무도 만나지 못했습니다.")
        return
    for other_id in c.relationships:
        other = state.characters[other_id]
        print(f"  → {other.name}: {relationship.relation_brief(state, c, other)}")


def cmd_map(state: GameState) -> None:
    print(f"\n🗺 Day {state.day} {state.clock()}")
    for key, (loc_name, cap) in LOCATIONS.items():
        people = [c.name for c in state.characters.values() if c.location == key]
        if people:
            print(f"  {loc_name}: {', '.join(people)}")


def cmd_log(state: GameState, n: int = 10) -> None:
    print(f"\n📜 최근 이벤트 로그:")
    events = state.events[-n:]
    if not events:
        print("  아직 기록이 없습니다.")
    for e in events:
        print(f"  [day {e.day} {e.time}] {e.summary or e.type}")


def cmd_bubbles(state: GameState, sim: Simulation) -> None:
    if not state.bubbles:
        print(" 💬 대기 중인 말풍선이 없습니다.")
        return
    # 응답형(고백)을 우선 표시. 배고픔 말풍선은 안내만 (feed로 해소)
    bubble = next((b for b in state.bubbles if b.kind == "confess_request"),
                  state.bubbles[0])
    print(f"\n💬 {bubble.text}")
    if bubble.kind == "confess_request":
        answer = input("   허락할까요? [y=해! / n=그만해] > ").strip().lower()
        state.bubbles.remove(bubble)
        result = sim.resolve_confession(bubble, approved=(answer == "y"))
        print_result(result)
    elif bubble.kind == "hungry":
        print("   feed 명령으로 밥을 주면 사라집니다. (예: feed 이름)")
    else:
        state.bubbles.remove(bubble)


def cmd_feed(state: GameState, name: str, food_name: str = "") -> None:
    if food_name and food_name not in items.FOODS:
        print(f" ❓ '{food_name}' 은(는) 없는 음식입니다. 목록: {', '.join(items.FOODS)}")
        return
    if name == "all":
        # 디버그 편의 명령: 전원에게 한꺼번에 음식 주기.
        # 음식 미지정 시 각자 보통 구간 음식을 골라 배고픔만 무난하게 해소
        for c in state.characters.values():
            if food_name:
                fid = items.FOODS.index(food_name)
            else:
                normals = [i for i in range(len(items.FOODS))
                           if items.preference_tier(c, i) == "normal"]
                fid = state.rng.choice(normals)
            print(" " + items.feed(state, c, fid))
        return
    c = find_char(state, name)
    if not c:
        return
    if not food_name:
        print("  음식 목록: " + ", ".join(items.FOODS))
        return
    print(" " + items.feed(state, c, items.FOODS.index(food_name)))


def main() -> None:
    parser = argparse.ArgumentParser(description="AI 토모다치 라이프 터미널 프로토타입")
    parser.add_argument("--provider", choices=["codex", "mock"], default="codex",
                        help="LLM 프로바이더 (기본: codex CLI)")
    parser.add_argument("--mock", action="store_true", help="--provider mock 의 줄임")
    parser.add_argument("--seed", type=int, default=None, help="랜덤 시드")
    parser.add_argument("--save-dir", default=os.path.join(BASE_DIR, "saves"))
    parser.add_argument("--new", action="store_true", help="저장이 있어도 새 마을로 시작")
    parser.add_argument("--script", help="명령을 세미콜론으로 이어서 비대화형 실행 (테스트용)")
    args = parser.parse_args()

    provider_name = "mock" if args.mock else args.provider
    llm = make_provider(provider_name)

    # 세이브가 있으면 자동 이어하기 (--new 로 새 마을 시작)
    state = None if args.new else load_game(args.save_dir)
    resumed = state is not None
    if state is None:
        state = build_new_game(os.path.join(BASE_DIR, "data", "characters.json"),
                               args.seed if args.seed is not None else random.randrange(10 ** 6))
    if args.seed is not None:
        state.rng = random.Random(args.seed)
    sim = Simulation(state, llm)

    if resumed:
        print(f"📂 저장된 마을을 이어서 시작합니다 — {state.village_name}, Day {state.day} {state.clock()}"
              f" (새 마을로 시작하려면: python3 main.py --new)")
    print(f"🏘 {state.village_name}에 오신 것을 환영합니다! (LLM: {provider_name})")
    print(f"   주민 {len(state.characters)}명이 살고 있습니다. "
          f"`auto` 를 입력하면 시간이 알아서 흐르며 마을 소식이 올라옵니다.")
    print(f"   (10틱마다 + 종료 시 자동 저장됩니다)\n")
    print(HELP)

    # ---------- 자동 진행 (백그라운드 스레드) ----------
    # 메인 스레드는 입력을 받고, 티커 스레드가 틱을 진행하며 이벤트를 출력한다.
    # 상태 변경은 lock으로 직렬화 (틱 진행 중에는 명령이 잠시 대기)
    lock = threading.Lock()
    auto_cfg = {"on": False, "interval": 3.0}

    # ---------- 자동 저장 ----------
    AUTOSAVE_EVERY = 10  # 10틱(게임 내 5시간)마다 자동 저장
    tick_count = {"n": 0}

    def after_tick() -> bool:
        # 매 틱 후 호출. 자동 저장이 일어났으면 True (알림 출력은 호출자 몫)
        tick_count["n"] += 1
        if tick_count["n"] % AUTOSAVE_EVERY:
            return False
        with lock:
            save_game(nonlocal_state["state"], args.save_dir)
        return True

    def prompt_text() -> str:
        st = nonlocal_state["state"]
        return f"\n[{st.village_name} d{st.day} {st.clock()}{' ▶' if auto_cfg['on'] else ''}] > "

    def redraw_prompt() -> None:
        # 비동기 출력 후 입력 줄을 다시 표시 (타이핑하던 내용은 터미널 버퍼에 유지됨)
        print(prompt_text(), end="", flush=True)

    def ticker_loop() -> None:
        bubble_notified = False
        while auto_cfg["on"]:
            time.sleep(auto_cfg["interval"])
            if not auto_cfg["on"]:
                break
            st = nonlocal_state["state"]
            if st.bubbles:
                # 응답 대기 중에는 시간 정지
                if not bubble_notified:
                    print("\n ⏸ 응답을 기다리는 말풍선이 있어 시간이 멈춰 있습니다. (`bubbles` 로 확인)")
                    redraw_prompt()
                    bubble_notified = True
                continue
            bubble_notified = False
            with lock:
                result = sim.tick()
            st = nonlocal_state["state"]
            if result.scene or result.messages:
                print(f"\n⏱ Day {st.day} {st.clock()}")
                print_result(result)
                if st.bubbles:
                    print(" ⏸ 응답이 필요한 말풍선이 도착해 시간을 멈춥니다. (`bubbles` 로 확인)")
                    bubble_notified = True
                elif result.major:
                    # 싸움/이별/베프·원수 성립 같은 큰 이벤트 → 자동 진행 일시정지
                    auto_cfg["on"] = False
                    print(" ⏸ 큰 이벤트가 일어나 자동 진행을 멈췄습니다. (`auto` 로 재개)")
                redraw_prompt()
            if after_tick():
                print("\n 💾 (자동 저장)")
                redraw_prompt()
            if not auto_cfg["on"]:
                break

    def handle(line: str) -> bool:
        # 명령 한 줄 처리. False 반환 시 종료
        parts = line.split()
        cmd = parts[0] if parts else "s"

        def print_tick(result) -> None:
            print(f"⏱ Day {state.day} {state.clock()}", end="")
            if result.scene or result.messages:
                print()
                print_result(result)
            else:
                print(" — 평화로운 시간이 흘러갑니다...")
            sys.stdout.flush()

        if cmd in ("quit", "exit", "q"):
            auto_cfg["on"] = False
            return False
        elif cmd in ("s", "step", ""):
            if not parts and auto_cfg["on"]:
                return True  # 자동 진행 중 빈 엔터는 프롬프트 새로고침만
            n = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
            for _ in range(n):
                with lock:
                    result = sim.tick()
                print_tick(result)
                if after_tick():
                    print(" 💾 (자동 저장)")
                # 응답 대기 말풍선이 생기면 진행 멈춤
                if state.bubbles:
                    break
        elif cmd == "auto":
            arg = parts[1] if len(parts) > 1 else ""
            if arg in ("off", "stop"):
                auto_cfg["on"] = False
                print(" ⏸ 자동 진행을 껐습니다.")
                return True
            if arg:
                try:
                    auto_cfg["interval"] = max(0.3, float(arg))
                except ValueError:
                    print(" ❓ 초 단위 숫자를 입력해 주세요. 예: auto 5")
                    return True
            if len(parts) > 2 and parts[2].isdigit():
                # 테스트용 동기 모드: auto <초> <틱수>
                for _ in range(int(parts[2])):
                    with lock:
                        result = sim.tick()
                    print_tick(result)
                    if after_tick():
                        print(" 💾 (자동 저장)")
                    if state.bubbles:
                        break
                    time.sleep(auto_cfg["interval"])
            elif not auto_cfg["on"]:
                auto_cfg["on"] = True
                threading.Thread(target=ticker_loop, daemon=True).start()
                print(f" ▶ 자동 진행 시작 ({auto_cfg['interval']:g}초/틱). "
                      f"이대로 명령을 입력해도 되고, `pause` 로 멈출 수 있어요.")
            else:
                print(f" ▶ 자동 진행 속도 변경: {auto_cfg['interval']:g}초/틱")
        elif cmd in ("pause", "stop"):
            auto_cfg["on"] = False
            print(" ⏸ 자동 진행을 껐습니다.")
        elif cmd == "status":
            cmd_status(state, parts[1] if len(parts) > 1 else "")
        elif cmd == "rel":
            if len(parts) > 1:
                cmd_rel(state, parts[1])
            else:
                cmd_relmap(state)
        elif cmd == "map":
            cmd_map(state)
        elif cmd == "log":
            cmd_log(state, int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10)
        elif cmd == "bubbles":
            with lock:
                cmd_bubbles(state, sim)
        elif cmd == "feed" and len(parts) > 1:
            with lock:
                cmd_feed(state, parts[1], parts[2] if len(parts) > 2 else "")
        elif cmd == "dex" and len(parts) > 1:
            c = find_char(state, parts[1])
            if c:
                print(items.food_dex(c))
        elif cmd == "give" and len(parts) > 2:
            # 도구 아이템: give <이름> <카메라|프라이팬>
            c = find_char(state, parts[1])
            tool = {"카메라": "camera", "프라이팬": "frying_pan"}.get(parts[2])
            if c and tool:
                with lock:
                    result = sim.use_tool(c, tool)
                print_result(result)
            elif c:
                print(" ❓ 도구 목록: 카메라, 프라이팬")
        elif cmd == "album":
            if not state.photos and not state.dishes:
                print(" 📒 아직 기록이 없습니다. (give <이름> 카메라/프라이팬)")
            for p in state.photos[-10:]:
                print(f"  🖼 '{p['title']}' — Day {p['day']} {p['author']} 촬영 (피사체: {p.get('subject', '?')})")
            for d in state.dishes[-10:]:
                print(f"  🍳 '{d['dish']}' — Day {d['day']} {d['author']}")
        elif cmd == "news":
            weird = len(parts) > 1 and parts[1] == "weird"
            with lock:
                result = sim.news_briefing(weird=weird)
            print_result(result)
        elif cmd == "save":
            with lock:
                save_game(state, args.save_dir)
            print(f" 💾 저장 완료: {args.save_dir}")
        elif cmd == "load":
            with lock:
                loaded = load_game(args.save_dir)
                if loaded is not None:
                    nonlocal_state["state"] = loaded
            if loaded is None:
                print(" ❓ 저장된 게임이 없습니다.")
            else:
                print(" 📂 불러오기 완료. (주의: 프로토타입에서는 load 후 새 객체로 교체됩니다)")
        elif cmd == "help":
            print(HELP)
        else:
            print(" ❓ 알 수 없는 명령입니다. `help` 를 입력해 보세요.")
        return True

    # load 명령이 state를 교체할 수 있도록 가변 컨테이너 사용
    nonlocal_state = {"state": state}

    if args.script:
        # 테스트용 비대화형 모드
        for line in args.script.split(";"):
            line = line.strip()
            print(f"\n>>> {line or '(엔터)'}")
            if not handle(line):
                break
            state = nonlocal_state["state"]
            sim.state = state
        return

    def save_and_exit() -> None:
        auto_cfg["on"] = False
        with lock:
            save_game(nonlocal_state["state"], args.save_dir)
        print(" 💾 마을을 저장했습니다. 안녕히 가세요!")

    while True:
        try:
            line = input(prompt_text()).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            save_and_exit()
            break
        if not handle(line):
            save_and_exit()
            break
        state = nonlocal_state["state"]
        sim.state = state


if __name__ == "__main__":
    main()
