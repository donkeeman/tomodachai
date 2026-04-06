import json
from unittest.mock import MagicMock

from tomodachai.conversation import (
    ConversationEngine,
    ConversationResult,
    DialogueLine,
    build_conversation_prompt,
)
from tomodachai.relationship import Relationship
from tomodachai.memory import SocialEvent


def test_dialogue_line_model():
    line = DialogueLine(speaker="민수", text="안녕!")
    assert line.speaker == "민수"


def test_conversation_result_model():
    result = ConversationResult(
        dialogue=[DialogueLine(speaker="민수", text="안녕!")],
        deltas={"민수": {"friendship": 5}, "지은": {"friendship": 3}},
        summary="인사를 나눴다",
    )
    assert len(result.dialogue) == 1
    assert result.deltas["민수"]["friendship"] == 5


def test_build_prompt_contains_character_info(
    char_minsu, char_jieun, sample_personalities,
):
    rel_ab = Relationship(friendship=30, romance=10)
    rel_ba = Relationship(friendship=25)
    prompt = build_conversation_prompt(
        char_a=char_minsu,
        char_b=char_jieun,
        personality_a=sample_personalities["nori_dynamo"],
        personality_b=sample_personalities["nagomi_dreamer"],
        rel_ab=rel_ab,
        rel_ba=rel_ba,
        memories=[],
        location="공원",
        time_of_day="오후",
    )
    assert "민수" in prompt
    assert "지은" in prompt
    assert "~인 거지" in prompt or "일반" in prompt
    assert "그치~?" in prompt or "일반" in prompt
    assert "공원" in prompt


def test_build_prompt_includes_memories(
    char_minsu, char_jieun, sample_personalities,
):
    memories = [
        SocialEvent(
            tick=1, participants=["char_1", "char_2"],
            event_type="conversation",
            summary="공원에서 처음 만나 인사를 나눴다",
            emotional_impact={"char_1": 0.3, "char_2": 0.2},
        ),
    ]
    prompt = build_conversation_prompt(
        char_a=char_minsu,
        char_b=char_jieun,
        personality_a=sample_personalities["nori_dynamo"],
        personality_b=sample_personalities["nagomi_dreamer"],
        rel_ab=Relationship(),
        rel_ba=Relationship(),
        memories=memories,
        location="카페",
        time_of_day="저녁",
    )
    assert "공원에서 처음 만나" in prompt


def test_engine_generate_parses_llm_response(
    char_minsu, char_jieun, sample_personalities, mock_llm,
):
    llm_response = {
        "dialogue": [
            {"speaker": "민수", "text": "지은 씨, 오늘 날씨 좋네요!"},
            {"speaker": "지은", "text": "그치~? 산책하기 딱이에요."},
        ],
        "deltas": {
            "민수": {"friendship": 3, "romance": 1, "tension": 0},
            "지은": {"friendship": 2, "romance": 0, "tension": 0},
        },
        "summary": "공원에서 만나 날씨 이야기를 나눴다",
    }
    mock_llm.chat_json.return_value = llm_response

    engine = ConversationEngine(mock_llm, sample_personalities)
    result = engine.generate(
        char_a=char_minsu,
        char_b=char_jieun,
        rel_ab=Relationship(),
        rel_ba=Relationship(),
        memories=[],
        location="공원",
        time_of_day="오후",
    )
    assert len(result.dialogue) == 2
    assert result.dialogue[0].speaker == "민수"
    assert result.deltas["민수"]["friendship"] == 3
    assert result.summary == "공원에서 만나 날씨 이야기를 나눴다"
    mock_llm.chat_json.assert_called_once()
