from fastapi.testclient import TestClient
from app import app
import time

client = TestClient(app)

def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_autocomplete_valid():
    response = client.get("/autocomplete?query=Mo")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_autocomplete_short_query():
    response = client.get("/autocomplete?query=M")
    assert response.status_code == 200
    assert response.json() == []

def test_get_weather_success():
    response = client.get("/weather?location=Moscow")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Moscow" in response.text or "Москва" in response.text

def test_get_weather_invalid_location():
    response = client.get("/weather?location=InvalidCityNameThatDoesNotExist123")
    assert response.status_code in [404, 500]

def test_get_location_stats():
    response = client.get("/location-stats")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_location_stats_increment():
    location = "Moscow"

    response_before = client.get("/location-stats")
    assert response_before.status_code == 200
    stats_before = {entry["city"]: entry["count"] for entry in response_before.json()}

    count_before = stats_before.get(location, 0)

    response_weather = client.get(f"/weather?location={location}")
    assert response_weather.status_code == 200

    time.sleep(0.5)

    response_after = client.get("/location-stats")
    assert response_after.status_code == 200
    stats_after = {entry["city"]: entry["count"] for entry in response_after.json()}

    count_after = stats_after.get(location, 0)
    assert count_after == count_before + 1