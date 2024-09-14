from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional
from faker import Faker
import random
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
import argparse
import uvicorn

# Initialize FastAPI and Faker
app = FastAPI(
    title="ServerAPI",
    description="API in Python. FastAPI is used.\nThere are functions for getting fake names, random numbers, and so on.",
    version="0.2"
)
fake = Faker()

# Define the data model for generating random numbers
class RandomNumberRequest(BaseModel):
    min: int
    max: int


@app.get("/")
def read_root():
    """Root endpoint for checking the API's status."""
    return {"message": "Welcome to the Faker and Random API!"}


@app.get("/fake/name")
def get_fake_name():
    return {"name": fake.name()}


@app.get("/fake/address")
def get_fake_address():
    return {"address": fake.address()}


@app.get("/fake/text")
def get_fake_text(max_nb_chars: Optional[int] = 200):
    return {"text": fake.text(max_nb_chars=max_nb_chars)}


@app.post("/random/number")
def get_random_number(request: RandomNumberRequest):
    if request.min > request.max:
        raise HTTPException(
            status_code=400, detail="Min value cannot be greater than max value."
        )
    return {"number": random.randint(request.min, request.max)}


@app.get("/fake/{method_name}")
def get_fake_data(method_name: str):
    try:
        faker_method = getattr(fake, method_name)
        result = faker_method()
        return {method_name: result}
    except AttributeError:
        raise HTTPException(status_code=404, detail="Faker method not found.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


class FastAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler class for FastAPI."""

    def do_GET(self):
        # Create a request to FastAPI using HTTP headers and request data
        response = self.proxy_request("GET")

        # Send the response to the client
        self.respond(response)

    def do_POST(self):
        # Create a request to FastAPI using HTTP headers and request data
        response = self.proxy_request("POST")

        # Send the response to the client
        self.respond(response)

    def proxy_request(self, method: str):
        # Prepare the request for FastAPI
        headers = {key: value for key, value in self.headers.items()}

        # Read the request body if it exists
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))

        # Use FastAPI as a handler to get the response
        async def call_fastapi():
            request = Request(
                {
                    "type": "http",
                    "method": method,
                    "headers": [
                        (k.encode("latin-1"), v.encode("latin-1"))
                        for k, v in headers.items()
                    ],
                    "body": body,
                }
            )

            # Proxy request to FastAPI for handling
            response = await app(request.scope, request.receive, request.send)
            return response

        # Run the async function using asyncio.run
        return call_fastapi()

    def respond(self, response: Response):
        # Convert the FastAPI response into an HTTP response
        self.send_response(response.status_code)
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.body)


# Function to run the HTTP server
def run_server(host: str, port: int):
    server_address = (host, port)
    httpd = HTTPServer(server_address, FastAPIHandler)
    print(f"Running HTTP server on {host}:{port}...")
    httpd.serve_forever()


# Main entry point with command-line argument support
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FastAPI with custom host and port.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host for the server.")
    parser.add_argument("--port", type=int, default=8000, help="Port for the server.")
    parser.add_argument("--fastapi-port", type=int, default=8001, help="Port for FastAPI application.")

    args = parser.parse_args()

    # Run the server in a separate thread
    Thread(target=run_server, args=(args.host, args.port)).start()

    # Simultaneously run the FastAPI application
    uvicorn.run(app, host=args.host, port=args.fastapi_port)
