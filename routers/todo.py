from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse
from models import Base, Todo
from database import engine, SessionLocal #SessionLocal'i kullanarak aslında veritabanıyla bağlantı sağlıyoruz
from typing import Annotated
from fastapi import APIRouter, Depends, Path, HTTPException, Request
from routers.auth import get_current_user
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import google.generativeai as genai
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
import markdown
from bs4 import BeautifulSoup

router = APIRouter(
    prefix="/todo",
    tags=["Todo"]
)

templates = Jinja2Templates(directory = "templates")

class TodoRequest(BaseModel): #API üzerinden post için class yazıyoruz. models.py'de ki classı kullanmicaz çünkü orada id var, id vermicek post yapan kişi. o yüzden yeni bir class yazıyoruz
    title: str = Field(min_length=3, max_length=15)
    description: str = Field(min_length=5, max_length=1000)
    priority: int = Field(gt=0, lt=6)
    complete: bool


def get_db(): #SessionLocal'i kullanarak database ile bağlantı kuracağımız fonksiyon burası. Bu fonksiyon bize veritabanını verir. Artık tüm database ile alakalı işlem yapacağımız fonksiyonlar, bu fonksiyondan depend edecek
    db = SessionLocal()
    try:
        yield db #yield return gibidir. Return'den farkı ise, return tek bir değer döndürürken yield birden fazla sequence döndürebilir. Fonksiyon üzerinde iterate edilebiliyor. Genel olarak SessionLocal kullanırken yield kullanılır. Burada bu fonksiyonu generator function yapmış olduk bu hareketle.
    finally:
        db.close() #session'u kapattık

db_dependency=Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

def redirect_to_login():
    redirect_response = RedirectResponse(url="/auth/login-page", status_code=302)
    redirect_response.delete_cookie("access_token") #kullanıcının kukisindeki tokeni bitmişse ya da saldırı vs yapıyorsa sil
    return redirect_response

@router.get("/todo-page") # todolarını görüntüleyeceğin todos sayfasının backend ile bağlandığı fonksiyon
async def render_todo_page(request: Request, db: db_dependency):

    try:
        user = await get_current_user(request.cookies.get('access_token')) # kullanıcının cookielerinin içerisine kaydettiğimiz access_token'a bak. Eğer kullanıcı kayıt olmuşsa sal izin ver, olmamışsa verme
        if user is None: # eğer kullanıcı yoksa, yani böyle bir kayıtlı kullanıcımız yoksa
            return redirect_to_login() # kayıt ol sayfasına yönlendir
        todos = db.query(Todo).filter(Todo.owner_id == user.get('id')).all()
        return templates.TemplateResponse("todo.html", {"request":request, "todos":todos, "user":user})
    except:
        return redirect_to_login()

@router.get("/add-todo-page") # todolarına todolar ekleyebileceğin add-todolar sayafsının backend ile frontendinin bağlandığı fonksiyon
async def render_add_todo_page(request: Request):

    try:
        user = await get_current_user(request.cookies.get('access_token')) # kullanıcının cookielerinin içerisine kaydettiğimiz access_token'a bak. Eğer kullanıcı kayıt olmuşsa sal izin ver, olmamışsa verme
        if user is None: # eğer kullanıcı yoksa, yani böyle bir kayıtlı kullanıcımız yoksa
            return redirect_to_login() # kayıt ol sayfasına yönlendir

        return templates.TemplateResponse("add-todo.html", {"request":request, "user":user})
    except:
        return redirect_to_login()

@router.get("/edit-todo-page/{todo_id}") # todolarını editleyeceğin edit todos sayfasının backend ile bağlandığı fonksiyon
async def render_todo_page(request: Request, todo_id: int, db: db_dependency):

    try:
        user = await get_current_user(request.cookies.get('access_token')) # kullanıcının cookielerinin içerisine kaydettiğimiz access_token'a bak. Eğer kullanıcı kayıt olmuşsa sal izin ver, olmamışsa verme
        if user is None: # eğer kullanıcı yoksa, yani böyle bir kayıtlı kullanıcımız yoksa
            return redirect_to_login() # kayıt ol sayfasına yönlendir

        todo = db.query(Todo).filter(Todo.id == todo_id).first()
        return templates.TemplateResponse("edit-todo.html", {"request":request, "todo":todo, "user":user})
    except:
        return redirect_to_login()

@router.get("/")
async def read_all(user: user_dependency, db: db_dependency): # bu fonksiyonun(todoları görme fonksiyonunun) çalışması için hem database'e bağlanması gerekli, hem de kullanıcı bilgilerinin de doğrulanması gerekli. Kullanıcı olmayan todoları göremeyecek
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return db.query(Todo).filter(Todo.owner_id == user.get('id')).all() # Bu filtrelemeyle birlikte artık her kullanıcı, kendine ait olan todoları görüntüleyebilecek. Herkesin todoları görüntüleyemeyecek

@router.get("/todo/{todo_id}")
async def get_by_id(user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0, lt=10)):
    todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get('id')).first()
    if todo is not None:
        return todo
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")

@router.post("/todo", status_code=status.HTTP_201_CREATED)
async def create_todo(user:user_dependency ,db: db_dependency, todo_request: TodoRequest):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kim ooo??")

    todo = Todo(**todo_request.dict(), owner_id = user.get('id')) # tam olarak bu satırda her todonun her kullanıcıya ayrı ayrı kaydedileceğini söyledik. Yani her kullanıcı sadece kendine todoları kaydedebilecek. Başka kullanıcılar başka kullanıcıların todolarını göremeyecek
    todo.description = create_todo_with_gemini(todo.description)
    db.add(todo)
    db.commit()

@router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user:user_dependency, db: db_dependency, todo_request:TodoRequest, todo_id: int = Path(gt=0, lt=10)):
    todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get('id')).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")

    todo.title = todo_request.title
    todo.description = todo_request.description
    todo.complete = todo_request.complete

    db.add(todo)
    db.commit()

@router.delete("/todo/{todo_id}", status_code=status.HTTP_200_OK)
async def delete_todo(user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0, lt=10)):
    todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get('id')).first()

    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    else:
        #db.query(Todo).filter(Todo.id==todo_id).delete()
        db.delete(todo)
        db.commit()

def markdown_to_text(markdown_string: str): #gemini çıktıyı **Konu: şeklinde veriyor. bu markdown olarak verdiği anlamına geliyor. burada bu markdownu güzelleştiriyoruz
    html = markdown.markdown(markdown_string)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()
    return text

def create_todo_with_gemini(todo_string: str):
    load_dotenv()
    genai.configure(api_key = os.environ.get("GOOGLE_API_KEY"))
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    response = llm.invoke(
        [
            HumanMessage(content="I will provide you a todo item to add my to do list. What I want you to do is to create a longer and compherensive description of that todo item, my next message will be my todo: "),
            HumanMessage(content=todo_string)
        ]
    )
    return markdown_to_text(response.content)