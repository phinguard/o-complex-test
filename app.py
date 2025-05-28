from fastapi import FastAPI, HTTPException, Cookie, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import requests
import requests_cache
import uuid

import database

USERAGENT = "TestWeatherApp/1.0-as-o"
CACHE_NAME = "weather_cache"
CACHE_EXPIRE = 3600

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

requests_cache.install_cache(CACHE_NAME, expire_after=CACHE_EXPIRE)
session = requests.Session()

WMO_CODES = {
    0: "Ясно", 1: "Преимущественно ясно", 2: "Переменная облачность", 3: "Пасмурно",
    45: "Туман", 48: "Туман с изморозью", 51: "Морось: слабая", 53: "Морось: умеренная",
    55: "Морось: сильная", 56: "Переохлаждённая морось: слабая", 57: "Переохлаждённая морось: сильная",
    61: "Дождь: слабый", 63: "Дождь: умеренный", 65: "Дождь: сильный",
    66: "Переохлаждённый дождь: слабый", 67: "Переохлаждённый дождь: сильный",
    71: "Снег: слабый", 73: "Снег: умеренный", 75: "Снег: сильный", 77: "Снежные зёрна",
    80: "Ливень: слабый", 81: "Ливень: умеренный", 82: "Ливень: сильный",
    85: "Снегопад: слабый", 86: "Снегопад: сильный",
    95: "Гроза", 96: "Гроза с градом: слабая", 99: "Гроза с градом: сильная"
}

class Weather(BaseModel):
    temperature: float
    windspeed: float
    winddirection: float
    weathercode: int
    time: str

def fetch_json(url: str, params: dict = None) -> dict:
    response = session.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def get_coordinates(location: str) -> tuple[float, float]:
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": location,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": USERAGENT
    }
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Ошибка при запросе к Nominatim")
    data = response.json()
    if not data:
        raise HTTPException(status_code=404, detail=f"Местоположение '{location}' не найдено")
    return float(data[0]["lat"]), float(data[0]["lon"])

def search_locations(query: str, limit: int = 5) -> List[str]:
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": limit,
        "featuretype": "city"
    }
    headers = {
        "User-Agent": "TestWeatherApp/1.0-as-o"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code != 200:
            return []
        
        data = response.json()
        suggestions = []
        
        for item in data:
            name = item.get('name', '')
            if name and name not in suggestions:
                suggestions.append(name)
        
        return suggestions
    
    except Exception as e:
        return []

def get_current_weather(lat: float, lon: float) -> dict:
    weather_url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "current_weather": True}
    weather_data = fetch_json(weather_url, params)
    current = weather_data.get("current_weather")
    if not current:
        raise HTTPException(status_code=500, detail="No current weather data available")
    return current

def render_weather_template(request: Request, location: str, weather: dict, session_id: str):
    description = WMO_CODES.get(weather['weathercode'], "Неизвестно")
    response = templates.TemplateResponse(request, "index.html", {
        "weather": weather,
        "location": location,
        "description": description,
        "session_id": session_id
    })
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return response

@app.get("/")
def index(request: Request, session_id: Optional[str] = Cookie(None)):
    last_location = None
    if session_id:
        history = database.get_last_history(session_id)
        if history:
            last_location = history.city
    return templates.TemplateResponse(request, "index.html", {"last_location": last_location})

@app.get("/autocomplete")
def autocomplete(query: str) -> List[str]:
    if len(query) < 2:
        return []
    
    suggestions = search_locations(query, limit=3)
    return suggestions

@app.get("/weather", response_model=Weather)
def get_weather(location: str, request: Request, session_id: Optional[str] = Cookie(None)):
    if not session_id:
        session_id = str(uuid.uuid4())

    lat, lon = get_coordinates(location)
    current_weather = get_current_weather(lat, lon)
    database.add_history(location, session_id)
    return render_weather_template(request, location, current_weather, session_id)

@app.get("/location-stats")
def get_location_stats(request: Request):
    stats = database.get_location_statistics()
    result = [{"city": city, "count": count} for city, count in stats]
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("weather_app:app", host="127.0.0.1", port=8000, reload=True)