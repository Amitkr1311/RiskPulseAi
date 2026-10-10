def test_health_reports_service_and_database(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "RiskPulse AI API",
        "version": "0.1.0",
        "database": {"status": "healthy"},
    }

