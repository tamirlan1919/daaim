# backend/app.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .users.routes import router as users_router
from .orders.routes import router as orders_router
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://daim-web-zeta.vercel.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(orders_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="127.0.0.1", port=8000, reload=True, workers=1)