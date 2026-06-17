"""플레이어 응답 대기 말풍선 (고백 허락 요청 / 배고픔 알림).

prototype/game/models.py `Bubble` 대응. 세션 한정(세이브 비대상).
"""

from __future__ import annotations

from pydantic import BaseModel


class Bubble(BaseModel):
    kind: str                      # confess_request / hungry
    char_id: int                   # 말풍선 주인
    target_id: int | None = None   # 고백 대상 (confess_request)
    text: str = ""                 # 표시 문구
