"""
Weather Dashboard — interactive UI using get_current_weather.
"""

import argparse
import json
import os
import sys
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import dotenv

dotenv.load_dotenv()

from my_mcp_server import get_current_weather

SERVE_PORT = int(os.getenv("WEATHER_DASHBOARD_PORT", "8080"))


def fetch_weather(city: str) -> dict:
    """Call get_current_weather MCP tool and parse JSON response."""
    raw = get_current_weather(city.strip())
    if raw.startswith("Error"):
        raise RuntimeError(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid weather response: {raw[:200]}") from exc


def aqi_label(index: int) -> tuple[str, str]:
    labels = {
        1: ("Good", "aqi-good"),
        2: ("Moderate", "aqi-moderate"),
        3: ("Unhealthy (Sensitive)", "aqi-sensitive"),
        4: ("Unhealthy", "aqi-unhealthy"),
        5: ("Very Unhealthy", "aqi-very-unhealthy"),
        6: ("Hazardous", "aqi-hazardous"),
    }
    return labels.get(index, ("Unknown", "aqi-unknown"))


def weather_emoji(code: int, is_day: int) -> str:
    mapping = {
        1000: "☀️" if is_day else "🌙",
        1003: "⛅", 1006: "☁️", 1009: "☁️", 1030: "🌫️",
        1063: "🌦️", 1066: "🌨️", 1069: "🌨️", 1072: "🌨️", 1087: "⛈️",
        1114: "❄️", 1117: "❄️", 1135: "🌫️", 1147: "🌫️",
        1150: "🌧️", 1153: "🌧️", 1168: "🌧️", 1171: "🌧️",
        1180: "🌦️", 1183: "🌧️", 1186: "🌧️", 1189: "🌧️",
        1192: "🌧️", 1195: "🌧️", 1198: "🌧️", 1201: "🌧️",
        1204: "🌨️", 1207: "🌨️", 1210: "🌨️", 1213: "❄️",
        1216: "❄️", 1219: "❄️", 1222: "❄️", 1225: "❄️",
        1237: "🌨️", 1240: "🌦️", 1243: "🌧️", 1246: "🌧️",
        1249: "🌨️", 1252: "🌨️", 1255: "🌨️", 1258: "❄️",
        1261: "🌨️", 1264: "🌨️",
        1273: "⛈️", 1276: "⛈️", 1279: "⛈️", 1282: "⛈️",
    }
    return mapping.get(code, "🌡️")


def gradient_for_condition(code: int, is_day: int) -> str:
    if code == 1000:
        return (
            "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
            if is_day
            else "linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)"
        )
    if code in (1063, 1150, 1153, 1180, 1183, 1186, 1189, 1192, 1195, 1240, 1243, 1246):
        return "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    if code in (1066, 1114, 1210, 1213, 1216, 1219, 1222, 1225, 1258):
        return "linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%)"
    if code in (1087, 1273, 1276, 1279, 1282):
        return "linear-gradient(135deg, #373b44 0%, #4286f4 100%)"
    if code in (1030, 1135, 1147):
        return "linear-gradient(135deg, #bdc3c7 0%, #2c3e50 100%)"
    return (
        "linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%)"
        if is_day
        else "linear-gradient(135deg, #141e30 0%, #243b55 100%)"
    )


def to_view_model(data: dict) -> dict:
    """Convert raw API response into a display-friendly JSON object."""
    loc = data["location"]
    cur = data["current"]
    cond = cur["condition"]
    aqi = cur.get("air_quality", {})
    aqi_index = int(aqi.get("us-epa-index", 0) or 0)
    aqi_text, aqi_class = aqi_label(aqi_index)
    icon = cond["icon"]
    if icon.startswith("//"):
        icon = "https:" + icon

    region = loc.get("region") or ""
    country = loc.get("country") or ""
    parts = [loc["name"], region, country]
    city_name = ", ".join(p for p in parts if p)

    return {
        "city": city_name,
        "localtime": loc["localtime"],
        "temp_c": cur["temp_c"],
        "feelslike_c": cur["feelslike_c"],
        "condition_text": cond["text"],
        "condition_emoji": weather_emoji(cond["code"], cur["is_day"]),
        "icon_url": icon,
        "humidity": cur["humidity"],
        "wind_kph": cur["wind_kph"],
        "wind_dir": cur["wind_dir"],
        "vis_km": cur["vis_km"],
        "aqi_index": aqi_index,
        "aqi_text": aqi_text,
        "aqi_class": aqi_class,
        "last_updated": cur["last_updated"],
        "background": gradient_for_condition(cond["code"], cur["is_day"]),
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


INTERACTIVE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>WEATHER DASHBOARD</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Inter', system-ui, sans-serif;
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
      transition: background 0.6s ease;
    }

    .container { width: 100%; max-width: 520px; }

    .header {
      text-align: center;
      margin-bottom: 1.25rem;
    }

    .header h1 {
      font-size: 1.75rem;
      font-weight: 700;
      letter-spacing: -0.03em;
      margin-bottom: 0.25rem;
    }

    .header p {
      font-size: 0.9rem;
      opacity: 0.85;
    }

    .search-form {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }

    .search-form input {
      flex: 1;
      padding: 0.85rem 1rem;
      border: none;
      border-radius: 14px;
      font-size: 1rem;
      background: rgba(255,255,255,0.92);
      color: #1a1a2e;
      outline: none;
      box-shadow: 0 4px 20px rgba(0,0,0,0.12);
    }

    .search-form input:focus {
      box-shadow: 0 4px 24px rgba(0,0,0,0.18), 0 0 0 3px rgba(255,255,255,0.35);
    }

    .search-form button {
      padding: 0.85rem 1.35rem;
      border: none;
      border-radius: 14px;
      background: rgba(255,255,255,0.95);
      color: #4a3f8c;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      box-shadow: 0 4px 20px rgba(0,0,0,0.12);
      transition: background 0.2s, transform 0.15s;
    }

    .search-form button:hover { background: #fff; transform: translateY(-1px); }
    .search-form button:disabled { opacity: 0.65; cursor: not-allowed; transform: none; }

    .error-msg {
      background: rgba(220, 53, 69, 0.9);
      padding: 0.75rem 1rem;
      border-radius: 12px;
      margin-bottom: 1rem;
      font-size: 0.9rem;
    }

    .card {
      background: rgba(255, 255, 255, 0.18);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-radius: 28px;
      border: 1px solid rgba(255, 255, 255, 0.35);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
      overflow: hidden;
    }

    .card.hidden { display: none; }

    .card.animate {
      animation: fadeIn 0.45s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(14px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .placeholder {
      text-align: center;
      padding: 3rem 1.5rem;
      opacity: 0.9;
    }

    .placeholder .icon { font-size: 3rem; margin-bottom: 0.75rem; }
    .placeholder p { font-size: 1rem; line-height: 1.5; }

    .hero {
      padding: 2rem 2rem 1.5rem;
      text-align: center;
    }

    .city {
      font-size: 1.5rem;
      font-weight: 600;
      letter-spacing: -0.02em;
      margin-bottom: 0.25rem;
    }

    .local-time {
      font-size: 0.85rem;
      opacity: 0.8;
      margin-bottom: 1.25rem;
    }

    .weather-main {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 1rem;
      margin-bottom: 0.5rem;
    }

    .weather-icon {
      width: 80px;
      height: 80px;
      filter: drop-shadow(0 4px 8px rgba(0,0,0,0.2));
    }

    .temp-block { text-align: left; }

    .temp {
      font-size: 4rem;
      font-weight: 700;
      line-height: 1;
      letter-spacing: -0.04em;
    }

    .temp sup {
      font-size: 1.5rem;
      font-weight: 400;
      vertical-align: super;
    }

    .condition {
      font-size: 1.15rem;
      font-weight: 500;
    }

    .feels-like {
      font-size: 0.95rem;
      opacity: 0.85;
      margin-top: 0.75rem;
    }

    .stats {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1px;
      background: rgba(255,255,255,0.15);
    }

    .stat {
      background: rgba(255,255,255,0.08);
      padding: 1.15rem 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }

    .stat-label {
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      opacity: 0.75;
    }

    .stat-value {
      font-size: 1.25rem;
      font-weight: 600;
    }

    .aqi-badge {
      display: inline-block;
      padding: 0.2rem 0.6rem;
      border-radius: 999px;
      font-size: 0.85rem;
      font-weight: 600;
    }

    .aqi-good { background: #2ecc71; color: #fff; }
    .aqi-moderate { background: #f1c40f; color: #333; }
    .aqi-sensitive { background: #e67e22; color: #fff; }
    .aqi-unhealthy { background: #e74c3c; color: #fff; }
    .aqi-very-unhealthy { background: #9b59b6; color: #fff; }
    .aqi-hazardous { background: #7f0000; color: #fff; }
    .aqi-unknown { background: rgba(255,255,255,0.3); }

    .footer {
      padding: 1rem 1.5rem;
      text-align: center;
      font-size: 0.78rem;
      opacity: 0.7;
      border-top: 1px solid rgba(255,255,255,0.15);
    }

    .loading {
      text-align: center;
      padding: 3rem 1.5rem;
      font-size: 1.05rem;
    }

    @media (max-width: 420px) {
      .temp { font-size: 3.2rem; }
      .hero { padding: 1.5rem 1.25rem 1rem; }
      .city { font-size: 1.25rem; }
      .stats { grid-template-columns: 1fr; }
      .search-form { flex-direction: column; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🌤️ WEATHER DASHBOARD</h1>
      <p>Enter a location and get live weather details!</p>
    </div>

    <form class="search-form" id="searchForm">
      <input
        type="text"
        id="cityInput"
        placeholder="Enter location (e.g., Delhi)"
        autocomplete="off"
        required
      />
      <button type="submit" id="submitBtn">Get Weather</button>
    </form>

    <div class="error-msg" id="errorMsg" hidden></div>

    <div class="card" id="weatherCard">
      <div class="placeholder" id="placeholder">
        <div class="icon">🌍</div>
        <p>Search for any city to see temperature, humidity, wind, visibility, and air quality — all on this screen.</p>
      </div>

      <div id="weatherContent" hidden>
        <div class="hero">
          <div class="city" id="cityName"></div>
          <div class="local-time" id="localTime"></div>
          <div class="weather-main">
            <img class="weather-icon" id="weatherIcon" src="" alt="" />
            <div class="temp-block">
              <div class="temp" id="temperature"></div>
              <div class="condition" id="condition"></div>
            </div>
          </div>
          <div class="feels-like" id="feelsLike"></div>
        </div>
        <div class="stats">
          <div class="stat">
            <span class="stat-label">💧 Humidity</span>
            <span class="stat-value" id="humidity"></span>
          </div>
          <div class="stat">
            <span class="stat-label">💨 Wind Speed</span>
            <span class="stat-value" id="wind"></span>
          </div>
          <div class="stat">
            <span class="stat-label">👁️ Visibility</span>
            <span class="stat-value" id="visibility"></span>
          </div>
          <div class="stat">
            <span class="stat-label">🌪️ Air Quality</span>
            <span class="stat-value" id="aqi"></span>
          </div>
        </div>
        <div class="footer" id="footer"></div>
      </div>

      <div class="loading" id="loading" hidden>⏳ Fetching weather…</div>
    </div>
  </div>

  <script>
    const form = document.getElementById('searchForm');
    const cityInput = document.getElementById('cityInput');
    const submitBtn = document.getElementById('submitBtn');
    const errorMsg = document.getElementById('errorMsg');
    const weatherCard = document.getElementById('weatherCard');
    const placeholder = document.getElementById('placeholder');
    const weatherContent = document.getElementById('weatherContent');
    const loading = document.getElementById('loading');

    function showError(message) {
      errorMsg.textContent = '⚠️ ' + message;
      errorMsg.hidden = false;
    }

    function hideError() {
      errorMsg.hidden = true;
    }

    function setLoading(isLoading) {
      submitBtn.disabled = isLoading;
      loading.hidden = !isLoading;
      if (isLoading) {
        placeholder.hidden = true;
        weatherContent.hidden = true;
      }
    }

    function renderWeather(data) {
      document.body.style.background = data.background;
      document.title = 'Weather — ' + data.city.split(',')[0];

      document.getElementById('cityName').textContent = '📍 ' + data.city;
      document.getElementById('localTime').textContent = 'Local time: ' + data.localtime;
      document.getElementById('weatherIcon').src = data.icon_url;
      document.getElementById('weatherIcon').alt = data.condition_text;
      document.getElementById('temperature').innerHTML = data.temp_c + '<sup>°C</sup>';
      document.getElementById('condition').textContent = data.condition_emoji + ' ' + data.condition_text;
      document.getElementById('feelsLike').innerHTML = '🌡️ Feels like <strong>' + data.feelslike_c + '°C</strong>';
      document.getElementById('humidity').textContent = data.humidity + '%';
      document.getElementById('wind').innerHTML = data.wind_kph + ' km/h <small>(' + data.wind_dir + ')</small>';
      document.getElementById('visibility').textContent = data.vis_km + ' km';
      document.getElementById('aqi').innerHTML =
        '<span class="aqi-badge ' + data.aqi_class + '">' + data.aqi_text + '</span>' +
        '<small style="opacity:0.8;margin-left:0.4rem;">AQI ' + (data.aqi_index || 'N/A') + '</small>';
      document.getElementById('footer').textContent =
        'Last updated: ' + data.last_updated + ' · Fetched ' + data.fetched_at;

      placeholder.hidden = true;
      weatherContent.hidden = false;
      weatherCard.classList.remove('animate');
      void weatherCard.offsetWidth;
      weatherCard.classList.add('animate');
    }

    async function fetchWeather(city) {
      hideError();
      setLoading(true);

      try {
        const res = await fetch('/api/weather?city=' + encodeURIComponent(city));
        const payload = await res.json();
        if (!res.ok) throw new Error(payload.error || 'Could not fetch weather');
        renderWeather(payload);
      } catch (err) {
        placeholder.hidden = false;
        weatherContent.hidden = true;
        showError(err.message);
      } finally {
        setLoading(false);
      }
    }

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const city = cityInput.value.trim();
      if (city) fetchWeather(city);
    });

    const presetCity = new URLSearchParams(window.location.search).get('city');
    if (presetCity) {
      cityInput.value = presetCity;
      fetchWeather(presetCity);
    }
  </script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/weather":
            city = parse_qs(parsed.query).get("city", [""])[0]
            if not city:
                self.send_json({"error": "Location is required"}, 400)
                return
            try:
                data = fetch_weather(city)
                self.send_json(to_view_model(data))
            except RuntimeError as exc:
                self.send_json({"error": str(exc)}, 400)
            return

        if parsed.path in ("/", "/index.html"):
            self.send_html(INTERACTIVE_HTML)
            return

        self.send_json({"error": "Not found"}, 404)


def open_in_chrome(url: str) -> None:
    chrome_paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for chrome in chrome_paths:
        if os.path.isfile(chrome):
            os.spawnl(os.P_DETACH, chrome, chrome, url)
            print(f"Opened in Chrome: {url}")
            return
    webbrowser.open(url)
    print(f"Opened in default browser: {url}")


def serve_dashboard(default_city: str | None = None) -> None:
    url = f"http://localhost:{SERVE_PORT}/"
    if default_city:
        url += f"?city={default_city}"

    server = HTTPServer(("127.0.0.1", SERVE_PORT), DashboardHandler)
    print(f"Weather dashboard running at {url}")
    print("Enter a location and click 'Get Weather' to view details.")
    open_in_chrome(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive weather dashboard using get_current_weather")
    parser.add_argument("--city", help="Pre-load weather for a city (e.g., Delhi)")
    args = parser.parse_args()
    serve_dashboard(args.city)


if __name__ == "__main__":
    main()
