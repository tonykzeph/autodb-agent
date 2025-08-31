from fastapi import FastAPI
from dotenv import load_dotenv
from app.database import connect_to_mongo, close_mongo_connection
from app.routers import documents

load_dotenv()

app = FastAPI(title="AutoDB Agent", version="1.0.0")

app.include_router(documents.router)

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

@app.get("/")
async def root():
    return {"message": "AutoDB Agent is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)