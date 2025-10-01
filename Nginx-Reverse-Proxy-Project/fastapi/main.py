from fastapi import FastAPI
import socket

app = FastAPI()
HOST = socket.gethostname()

@app.get("/")
def root():
    return {"message": "Hello from FastAPI behind Nginx!", "host": HOST}

@app.get("/healthz")
def health():
    return {"ok": True, "host": HOST}