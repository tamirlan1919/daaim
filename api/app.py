# backend/app.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .users.routes import router as users_router
from .orders.routes import router as orders_router
from .products.routes import router as products_router
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 👈 разрешаем все домены
    allow_credentials=False,  # 👈 обязательно False, если allow_origins=["*"]
    allow_methods=["*"],  # 👈 разрешаем все методы (GET, POST, PUT, DELETE и т.д.)
    allow_headers=["*"],  # 👈 разрешаем все заголовки
)


app.include_router(users_router)
app.include_router(orders_router)
app.include_router(products_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="127.0.0.1", port=8000, reload=True, workers=1)