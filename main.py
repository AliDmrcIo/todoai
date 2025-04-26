from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from models import Base
from database import engine, SessionLocal #SessionLocal'i kullanarak aslında veritabanıyla bağlantı sağlıyoruz
from routers.auth import router as auth_router
from routers.todo import router as todo_router

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static") #frontendi bağlamak için yapıyoruz bunu. Bu proje içerisindeki static files içerisinde dedik

@app.get("/")
def read_root(request: Request): # bize gelen tüm istekleri fastapi request sınıfı sayesinde takip edebiliriz
    return RedirectResponse(url="/todo/todo-page",status_code=302) # biri girdiğinde onu todoo sayfasına yönlendiricez dedik

app.include_router(auth_router) #auth.py sayfasındaki routerları ekle ve tek bir sayfada onu da görek
app.include_router(todo_router) #todoo sayfasındaki routeri da topla gel

Base.metadata.create_all(bind=engine)