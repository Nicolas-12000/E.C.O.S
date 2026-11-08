from datetime import date

from fastapi.testclient import TestClient

from app.api.routes.chat import (
    _detect_intent,
    _resolve_intent,
    _rewrite_followup_as_full_question,
    _outlook_narrative,
)
from app.main import app

client = TestClient(app)


def test_chat_returns_context():
    response = client.post(
        "/api/chat",
        json={"question": "Resume la arquitectura final de ECOS y sus componentes principales."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert "sources" in payload
    assert isinstance(payload["sources"], list)


def test_outlook_compares_today_with_last_db_year():
    text = _outlook_narrative(
        place="Nariño",
        disease="dengue",
        today=date(2026, 11, 7),
        epi_week=45,
        by_year={2021: 80, 2022: 120},
        channel_p90=400,
    )
    assert "2022" in text
    assert "120 casos" in text
    assert "aumentar" in text
    assert "33,3%" in text
    assert "brote" in text
    assert "señal de brote" not in text

    intent = _detect_intent("cómo estará el dengue en nariño hoy")
    assert intent["disease"] == "dengue"
    assert intent["departamento_code"] == "52"
    assert intent["wants_outlook"] is True
    assert intent["fecha"] is not None
    assert intent["fecha"].fecha == date.today()


def test_detect_intent_sika_alias():
    intent = _detect_intent("y el sika")
    assert intent["disease"] == "zika"


def test_rewrite_followup_replaces_disease_keeps_place():
    full = _rewrite_followup_as_full_question(
        "cómo estará el dengue en nariño hoy",
        "y el sika",
    )
    assert "zika" in full.lower()
    assert "nariño" in full.lower()
    assert "dengue" not in full.lower()


def test_mobility_question_sets_flags():
    intent = _detect_intent("¿Movilidad y riesgo?")
    assert intent["wants_mobility"] is True


def test_brotes_pacifico_general_intent():
    intent = _detect_intent("Brotes en el Pacífico")
    assert intent["wants_brotes"] is True
    assert intent["region_norm"] == "PACIFICO"
    assert intent["wants_region"] is True


def test_resolve_intent_conversational_followup():
    history = [
        {"role": "user", "content": "cómo estará el dengue en nariño hoy"},
        {"role": "assistant", "content": "respuesta dengue"},
    ]
    intent, data_q = _resolve_intent("y el sika", history)
    assert intent["disease"] == "zika"
    assert intent["departamento_code"] == "52"
    assert intent["wants_outlook"] is True
    assert "zika" in data_q.lower() and "nariño" in data_q.lower()