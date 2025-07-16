from fastapi import FastAPI

app = FastAPI(
    title="Fast API Bank Fraud Detection ML",
    description="Fully featured banking API built with FastAPI",
)


@app.get("/")
def home():
    return {"message": "Welcome to the NextGen Bank API!"}
