from app.db.models import Article


def test_nlp_and_signal_endpoints(client, db_session) -> None:
    article = Article(
        source="news",
        title="RBI rate decision",
        text="The central bank changed interest rate policy.",
        content_hash="api-nlp-article",
        is_demo=True,
        processing_status="pending",
    )
    db_session.add(article)
    db_session.commit()

    status_response = client.get("/nlp/status")
    assert status_response.status_code == 200
    assert status_response.json()["sentiment_backend"] == "heuristic"

    process_response = client.post("/nlp/process-pending", json={"limit": 1})
    assert process_response.status_code == 200
    assert process_response.json()["processed"] == 1

    signals_response = client.get("/signals?event_type=macroeconomic")
    assert signals_response.status_code == 200
    body = signals_response.json()
    assert body["total"] == 1
    signal_id = body["items"][0]["id"]
    detail_response = client.get(f"/signals/{signal_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["impact_score"] in range(1, 11)


def test_process_article_returns_not_found(client) -> None:
    response = client.post("/nlp/process/999999")
    assert response.status_code == 404
