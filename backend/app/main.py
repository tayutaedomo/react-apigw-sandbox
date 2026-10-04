from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.request_logging import RequestLoggingMiddleware


class HelloResponse(BaseModel):
    message: str


app = FastAPI(title="Sandbox API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=[],
)
app.add_middleware(RequestLoggingMiddleware)


@app.get("/hello", response_model=HelloResponse)
def hello() -> HelloResponse:
    return HelloResponse(message="Hello World")
