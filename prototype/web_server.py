#!/usr/bin/env python3
# 웹 PoC 서버: 기존 터미널 프로토타입의 시뮬레이션(game/)을 그대로 '뇌'로 쓰고,
# Three.js 프론트엔드(web/)에 상태/이벤트를 JSON으로 제공한다.
# 기획서(00-overview)의 Python 백엔드 자리를 표준 라이브러리만으로 대체한 검증용.
# 주의: 관찰 전용 PoC라 세이브를 읽지도 쓰지도 않음 (터미널판 세이브와 충돌 방지)
from __future__ import annotations

import argparse
import datetime
import functools
import json
import os
import random
import signal
import sys
import threading
import time
from collections import deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from game import items, relationship                    # noqa: E402
from game.llm import make_provider                      # noqa: E402
from game.save import load_game, save_game              # noqa: E402
from game.simulation import (DAY_START, LOCATIONS, SLEEP_HOUR,  # noqa: E402
                             Simulation, TickResult)
from main import build_new_game                         # noqa: E402

AUTOSAVE_TICKS = 10     # 터미널판과 동일한 자동 저장 주기
REALTIME_CHECK = 30.0   # 리얼타임 모드 체크 간격(현실 초)
WAKE_MINUTES = DAY_START + 120  # 기상 7시


class WebGame:
    """시뮬레이션 본체 + 틱 결과 링버퍼. 모든 접근은 lock으로 직렬화."""

    def __init__(self, provider_name: str, seed: int, interval: float,
                 save_dir: str = None, fresh: bool = False):
        self.provider_name = provider_name
        self.save_dir = save_dir
        loaded = None if (fresh or not save_dir) else load_game(save_dir)
        self.resumed = loaded is not None
        self.state = loaded or build_new_game(
            os.path.join(BASE_DIR, "data", "characters.json"), seed)
        self.sim = Simulation(self.state, make_provider(provider_name))
        self.lock = threading.Lock()
        self.events: deque = deque(maxlen=300)
        self.seq = 0
        self.interval = interval        # None이면 리얼타임 모드 (현실 1분 = 게임 1분)
        self.asleep = False
        self._rolled = None             # 하루 전환을 마친 날짜 (리얼타임)
        self._ticks_since_save = 0

    def save(self) -> None:
        # lock을 잡은 상태에서 호출
        if self.save_dir:
            save_game(self.state, self.save_dir)
            self._ticks_since_save = 0

    def _push_result(self, result) -> dict:
        # TickResult를 이벤트 링버퍼에 직렬화 (lock 잡은 상태에서 호출)
        self.seq += 1
        ev = {
            "seq": self.seq,
            "day": self.state.day,
            "clock": self.state.clock(),
            "scene": result.scene,
            "dialogue": [[s, t] for s, t in result.dialogue],
            "messages": list(result.messages),
            "major": result.major,
        }
        self.events.append(ev)
        return ev

    def ticker(self) -> None:
        if self.interval is None:
            # 리얼타임 모드 (기본): 현실 시계와 1:1 동기화 (03 문서 '실시간 연동')
            while True:
                time.sleep(REALTIME_CHECK)
                try:
                    self._realtime_step()
                except Exception as exc:
                    print(f"[realtime 오류] {exc}", file=sys.stderr)
        # 터보(턴제) 모드: --interval 초마다 게임 30분 틱
        while True:
            time.sleep(self.interval)
            try:
                with self.lock:
                    result = self.sim.tick()
                    if result.scene or result.dialogue or result.messages:
                        self._push_result(result)
                    self._ticks_since_save += 1
                    if self._ticks_since_save >= AUTOSAVE_TICKS:
                        self.save()
            except Exception as exc:  # 어떤 예외에도 티커는 유지
                print(f"[tick 오류] {exc}", file=sys.stderr)

    def _realtime_step(self, now: datetime.datetime = None) -> None:
        # 현실 1분 = 게임 1분. 캐치업 시뮬 없음 (06 문서 범위 외 — 꺼져 있던 시간은 그냥 흘려보냄)
        now = now or datetime.datetime.now()
        real_min = now.hour * 60 + now.minute
        with self.lock:
            state = self.state
            if self._rolled is None:
                # 부팅 기준일: 새벽 5시 이전이면 오늘 전환이 아직 남아 있음
                self._rolled = (now.date() if real_min >= DAY_START
                                else now.date() - datetime.timedelta(days=1))
            elif real_min >= DAY_START and self._rolled != now.date():
                # 새벽 5시 하루 전환 (가동 중 하루 1회)
                result = TickResult()
                self.sim.day_rollover(result)
                self._push_result(result)
                self.save()
                self._rolled = now.date()

            # 취침 시간 (23시 직전 ~ 아침 7시): 이벤트 없이 시계만 흐름
            self.asleep = real_min >= SLEEP_HOUR * 60 - 5 or real_min < WAKE_MINUTES
            if self.asleep:
                state.minutes = real_min
                return

            delta = real_min - state.minutes
            if delta <= 0:
                state.minutes = real_min  # 부팅/이어하기 직후 동기화
                return
            result = self.sim.tick(tick_minutes=min(delta, 5))
            state.minutes = real_min      # 현실 시계와 재동기화
            if result.scene or result.dialogue or result.messages:
                self._push_result(result)
            self._ticks_since_save += 1
            if self._ticks_since_save >= AUTOSAVE_TICKS:
                self.save()

    # ---------- 플레이어 개입 (터미널판 feed / bubbles 명령과 동일 로직) ----------

    def feed(self, char_id: int, food_id: int) -> dict:
        with self.lock:
            char = self.state.characters.get(char_id)
            if char is None:
                return {"error": "없는 주민입니다"}
            if not (0 <= food_id < len(items.FOODS)):
                return {"error": "없는 음식입니다"}
            msg = items.feed(self.state, char, food_id)
            self.seq += 1
            self.events.append({
                "seq": self.seq, "day": self.state.day, "clock": self.state.clock(),
                "scene": "", "dialogue": [], "messages": [msg], "major": False,
            })
            self.save()  # 플레이어 개입은 즉시 저장
            return {"message": msg}

    def answer_bubble(self, index: int, char_name: str, allow: bool) -> dict:
        with self.lock:
            state = self.state
            if not (0 <= index < len(state.bubbles)):
                return {"error": "이미 처리된 말풍선입니다"}
            bubble = state.bubbles[index]
            if state.characters[bubble.char_id].name != char_name:
                return {"error": "말풍선이 갱신되었습니다. 다시 시도해 주세요"}
            if bubble.kind == "hungry":
                return {"error": "배고픔 말풍선은 밥을 주면 사라져요"}
            state.bubbles.pop(index)
            if bubble.kind != "confess_request":
                return {"message": "말풍선을 확인했습니다"}
            # 고백 허락/만류 → 결과 장면은 이벤트 스트림으로 재생됨
            result = self.sim.resolve_confession(bubble, approved=allow)
            self._push_result(result)
            self.save()  # 플레이어 개입은 즉시 저장
            return {"scene": result.scene, "messages": result.messages}

    def manual_save(self) -> dict:
        with self.lock:
            if not self.save_dir:
                return {"error": "세이브 폴더가 설정되지 않은 서버입니다"}
            self.save()
            return {"message": f"💾 저장 완료 (Day {self.state.day})"}

    def reset(self) -> dict:
        # 새 마을 시작 (현재 마을은 세이브까지 덮어씀)
        with self.lock:
            self.state = build_new_game(
                os.path.join(BASE_DIR, "data", "characters.json"),
                random.randrange(10 ** 6))
            self.sim = Simulation(self.state, make_provider(self.provider_name))
            self.events.clear()
            self.asleep = False
            self._rolled = None
            self.save()
            return {"message": "🔄 새 마을이 시작되었습니다"}

    def give(self, char_id: int, tool: str) -> dict:
        # 도구 아이템 지급 (05 문서: 카메라/프라이팬)
        with self.lock:
            char = self.state.characters.get(char_id)
            if char is None:
                return {"error": "없는 주민입니다"}
            if tool not in ("camera", "frying_pan"):
                return {"error": "없는 도구입니다"}
            result = self.sim.use_tool(char, tool)
            self._push_result(result)
            self.save()
            return {"messages": result.messages}

    def _rankings(self) -> dict:
        # 공원 랭킹보드 (03 문서): 순위만 공개, 수치는 비공개 원칙 유지
        state = self.state
        chars = state.characters
        couples, seen = [], set()
        for c in chars.values():
            lid = c.slots["lover"]
            if lid is None or (lid, c.id) in seen:
                continue
            seen.add((c.id, lid))
            o = chars[lid]
            ra = c.relationships.get(o.id)
            rb = o.relationships.get(c.id)
            score = sum(r.friendship + r.romance for r in (ra, rb) if r)
            couples.append((score, f"{c.name} ❤ {o.name}"))
        couples.sort(reverse=True)

        popular = {"M": [], "F": []}
        for c in chars.values():
            incoming = sum(o.relationships[c.id].romance for o in chars.values()
                           if o.id != c.id and c.id in o.relationships)
            popular[c.gender].append((incoming, c.name))
        for g in popular:
            popular[g].sort(reverse=True)

        fights = {}
        for e in state.events:
            if e.type == "fight" and len(e.participants) == 2:
                key = tuple(sorted(e.participants))
                fights[key] = fights.get(key, 0) + 1
        fight_top = sorted(((n, k) for k, n in fights.items()), reverse=True)

        return {
            "best_couple": [name for _s, name in couples[:3]],
            "popular_m": [n for s, n in popular["M"][:3] if s > 0],
            "popular_f": [n for s, n in popular["F"][:3] if s > 0],
            "fighters": [f"{chars[k[0]].name} ✕ {chars[k[1]].name} ({n}회)"
                         for n, k in fight_top[:3]],
        }

    def snapshot(self, since: int) -> dict:
        with self.lock:
            state = self.state
            chars = []
            for char in state.characters.values():
                def name_of(cid):
                    return state.characters[cid].name if cid else None
                crushes = [state.characters[oid].name
                           for oid, rel in char.relationships.items()
                           if rel.spark and char.slots["lover"] != oid]
                # 친구 순위: 만나본 상대를 우정 순으로 (표시는 수치 비공개 원칙대로 상태 텍스트)
                met = sorted(char.relationships.items(),
                             key=lambda kv: kv[1].friendship, reverse=True)
                friends = [{
                    "name": state.characters[oid].name,
                    "label": relationship.relation_brief(state, char, state.characters[oid]),
                } for oid, _rel in met[:5]]
                # 음식 도감: 먹여본 것만 선호 구간 공개 (전체 순위는 도감 발견 재미 유지)
                dex = [{"name": items.FOODS[fid], "tier": items.preference_tier(char, fid)}
                       for fid in range(len(items.FOODS)) if char.food_eaten[fid]]
                chars.append({
                    "id": char.id,
                    "name": char.name,
                    "gender": char.gender,
                    "location": char.location,
                    "mood": char.mood.label(),
                    "hunger": round(char.hunger),
                    "satisfaction": round(char.satisfaction),
                    "lover": name_of(char.slots["lover"]),
                    "best_friend": name_of(char.slots["best_friend"]),
                    "enemy": name_of(char.slots["enemy"]),
                    "crushes": crushes,
                    "food_eaten": list(char.food_eaten),
                    "friends": friends,
                    "dex": dex,
                })
            bubbles = [{
                "kind": b.kind,
                "char": state.characters[b.char_id].name,
                "target": state.characters[b.target_id].name if b.target_id else None,
                "text": b.text,
            } for b in state.bubbles]
            return {
                "village": state.village_name,
                "provider": self.provider_name,
                "day": state.day,
                "clock": state.clock(),
                "minutes": state.minutes,
                "seq": self.seq,
                "locations": {key: label for key, (label, _cap) in LOCATIONS.items()},
                "foods": items.FOODS,
                "rankings": self._rankings(),
                "asleep": self.asleep,
                "realtime": self.interval is None,
                "photos": list(reversed(state.photos[-40:])),
                "dishes": list(reversed(state.dishes[-40:])),
                "characters": chars,
                "events": [e for e in self.events if e["seq"] > since],
                "bubbles": bubbles,
            }


class Handler(SimpleHTTPRequestHandler):
    game: WebGame = None  # main()에서 주입

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/snapshot":
            qs = parse_qs(parsed.query)
            try:
                since = int(qs.get("since", ["0"])[0])
            except ValueError:
                since = 0
            body = json.dumps(self.game.snapshot(since), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "잘못된 요청 본문"})
            return
        if parsed.path == "/api/feed":
            out = self.game.feed(int(payload.get("char_id", -1)), int(payload.get("food_id", -1)))
        elif parsed.path == "/api/bubble":
            out = self.game.answer_bubble(int(payload.get("index", -1)),
                                          str(payload.get("char", "")),
                                          payload.get("answer") == "allow")
        elif parsed.path == "/api/give":
            out = self.game.give(int(payload.get("char_id", -1)),
                                 str(payload.get("tool", "")))
        elif parsed.path == "/api/save":
            out = self.game.manual_save()
        elif parsed.path == "/api/reset":
            out = self.game.reset()
        else:
            self._json(404, {"error": "없는 API"})
            return
        self._json(400 if "error" in out else 200, out)

    def log_message(self, *args):  # 정적 파일 요청 로그 소음 제거
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="AI 우리 동네 이야기 — 웹 3D PoC 서버")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--interval", type=float, default=None,
                        help="터보 모드: N초마다 게임 30분 틱 (생략 시 리얼타임: 현실 1분=게임 1분)")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--codex", action="store_true",
                        help="실제 Codex CLI로 대사 생성 (기본은 mock 고정 대사)")
    parser.add_argument("--save-dir", default=os.path.join(BASE_DIR, "saves_web"),
                        help="세이브 폴더 (터미널판 saves/ 와 분리, 기본 saves_web/)")
    parser.add_argument("--new", action="store_true", help="저장이 있어도 새 마을로 시작")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else random.randrange(10 ** 6)
    provider = "codex" if args.codex else "mock"
    game = WebGame(provider, seed, args.interval, save_dir=args.save_dir, fresh=args.new)
    Handler.game = game

    threading.Thread(target=game.ticker, daemon=True).start()

    handler = functools.partial(Handler, directory=os.path.join(BASE_DIR, "web"))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    where = "이어하기" if game.resumed else "새 마을"
    mode = ("⏰ 리얼타임 (현실 1분=게임 1분, 23시~7시 취침)" if args.interval is None
            else f"⏩ 터보 {args.interval}초/틱")
    print(f"🌐 http://127.0.0.1:{args.port}  ({provider}, {mode}, 💾 {where} — "
          f"Day {game.state.day}, 자동 저장 → {args.save_dir})")

    # SIGTERM(kill)도 Ctrl+C처럼 저장 후 종료
    def _term(_sig, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, _term)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    with game.lock:
        game.save()
    print(f"\n💾 저장 완료 (Day {game.state.day}) — 서버 종료")


if __name__ == "__main__":
    main()
