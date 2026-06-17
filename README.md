# MCP-Based Weather Information System

A Python-based project that provides weather information using MCP tools and includes a simple web
dashboard for viewing weather details. The project integrates WeatherAPI for live weather data and
Google Gemini API for AI-powered responses through FastMCP.

---

## Features

* **MCP Server**

* Retrieves current weather information for any location.
* Generates AI-powered responses using Google Gemini.

* **Weather Dashboard**

* Provides an interactive and user-friendly interface.
* Displays weather details for the selected city instantly.

---

## Project Structure

```text
MCP/
├── my_mcp_server.py      # MCP and HTTP server
├── weather_dashboard.py  # Weather dashboard UI
├── weather.html          # Legacy static page
├── .env                  # API keys and setup
└── venv/                 # Virtual environment
```

---

## Requirements

* Python 3.10 or higher
* WeatherAPI API key
* Google Gemini API key

---

## Installation

### 1. Create a Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```powershell
pip install mcp python-dotenv requests google-genai
```

### 3. Create a `.env` File

```env
GOOGLE_API_KEY=your_google_api_key
WEATHER_API_KEY=your_weather_api_key
WEATHER_API_BASE_URL=https://api.weatherapi.com/v1
MCP_SERVER_PORT=8001
HTTP_SERVER_PORT=8002
WEATHER_DASHBOARD_PORT=8080
```

---

## Running the Weather Dashboard

Start the dashboard:

```powershell
python weather_dashboard.py
```

Open:

```text
http://localhost:8080
```

### Steps

1. Enter a location (e.g., Delhi).
2. Click the Get Weather button.
3. View weather details instantly.

---

## Running the MCP Server

Start the server:

```powershell
python my_mcp_server.py
```

### Health Check

```powershell
curl http://localhost:8002/health
```

### Example Tool Request

```powershell
curl -X POST http://localhost:8002/ `
-H "Content-Type: application/json" `
-d '{"tool":"get_current_weather","args":{"location":"London"}}'
```

---

## Available MCP Tools

| Tool                       | Description                                         |
| -------------------------- | --------------------------------------------------- |
| `get_current_weather`      | Returns current weather information for a location. |
| `generate_gemini_response` | Generates AI-powered responses using Google Gemini. |

---

## Notes

* Use accurate city names for better results.
* Keep the .env file secure and private.

---

## Technologies Used

* **Python** – Core programming language used for developing the application.
* **FastMCP** – Framework used to create and manage MCP tools and services.
* **Requests** – Python library used for making HTTP requests to external APIs.
* **Python Dotenv** – Used to load environment variables from a .env file.
* **Google Gemini API** – Used to generate AI-powered text responses.
* **WeatherAPI** – Provides real-time weather data for different locations.
* **HTML, CSS, and JavaScript** – Used to create an interactive web interface.

---

## Project Results

### Image 1: Weather Dashboard Home Interface 

<img width="720" height="350"
       src="https://github.com/user-attachments/ass/4a828d20-bbc6-487e-b4b9-58c4b8b816ab"
       alt="Image">
</p>

### Image 2: Real-Time Weather Information Interface

<img width="720" height="350"
       src="https://github.com/user-attachments/assts/4a828d20-bbc6-487e-b4b9-58c4b8b816ab"
       alt="Image">
</p>

---