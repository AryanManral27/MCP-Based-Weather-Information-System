import logging
import os
import threading
import requests
from mcp.server.fastmcp import FastMCP
import dotenv
from google import genai
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

# Load environment variables
dotenv.load_dotenv()

name = "MCP Server"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(name)


def get_env_variable_int(var_name: str, default: int) -> int:
    val = os.getenv(var_name)
    if val is None:
        return default
    return int(val)


mcp_port = get_env_variable_int("MCP_SERVER_PORT", 8001)
http_port = get_env_variable_int("HTTP_SERVER_PORT", 8002)  # FIX: separate port for HTTP

gemini_api_key = os.getenv("GOOGLE_API_KEY")
weather_api_key = os.getenv("WEATHER_API_KEY")
weather_api_BASE_URL = os.getenv("WEATHER_API_BASE_URL")

myMCP = FastMCP(name=name, port=mcp_port)


# ---------------- WEATHER TOOL ----------------
@myMCP.tool()
def get_current_weather(location: str) -> str:
    """Get current weather data for a given location"""
    logger.info("MCP Tool called get_current_weather()")

    if not weather_api_key or not weather_api_BASE_URL:
        return "Error: WEATHER_API_KEY or WEATHER_API_BASE_URL not configured."

    try:
        endpoint = f"{weather_api_BASE_URL}/current.json"
        params = {
            "key": weather_api_key,
            "q": location,
            "aqi": "yes",
            "lang": "en",
        }
        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()
        return response.text

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {e}")
        return f"Error fetching weather data for {location}: {e}"


# ---------------- GEMINI TOOL ----------------
@myMCP.tool()
def generate_gemini_response(prompt: str) -> str:
    """Generate response using Gemini API"""
    logger.info("MCP Tool called generate_gemini_response()")

    if not gemini_api_key:
        return "Error: GOOGLE_API_KEY not configured."

    try:
        client = genai.Client(api_key=gemini_api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text

    except Exception as e:
        logger.error(f"Gemini error: {str(e)}")
        return f"Error generating Gemini response: {str(e)}"

    # FIX: removed invalid client.close() — genai.Client has no close() method


# ---------------- TOOL MAP ----------------
TOOL_MAP = {
    "get_current_weather": get_current_weather,
    "generate_gemini_response": generate_gemini_response,
}


# ---------------- HTTP HANDLER ----------------
class ToolHandler(BaseHTTPRequestHandler):

    def send_json(self, payload, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, format, *args):
        logger.info(f"HTTP {self.address_string()} - {format % args}")

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/health"):
            self.send_json({"status": "running", "server": name})
        else:
            self.send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            request_json = json.loads(post_data)
            tool_name = request_json.get("tool")
            tool_args = request_json.get("args", {})

            if tool_name in TOOL_MAP:
                result = TOOL_MAP[tool_name](**tool_args)
                response = {"result": result}
            else:
                response = {"error": f"Tool '{tool_name}' not found"}

        except json.JSONDecodeError:
            response = {"error": "Invalid JSON request"}
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            response = {"error": str(e)}

        self.send_json(response)


# ---------------- MAIN ----------------
if __name__ == "__main__":
    logger.info(f"Starting {name}")

    # FIX: use SSE transport to avoid stdio EOF/JSON parsing errors
    mcp_thread = threading.Thread(target=lambda: myMCP.run(transport="sse"), daemon=True)
    mcp_thread.start()
    logger.info(f"MCP Server (SSE) started on port {mcp_port}")

    # Start HTTP server on its own port (main thread)
    server = HTTPServer(("0.0.0.0", http_port), ToolHandler)
    logger.info(f"HTTP Server running on port {http_port}")
    print(f"\n  HTTP Server: http://localhost:{http_port}\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")