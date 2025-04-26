from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from starlette import status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer #kullanıcının girdiği password ve username'import daha düzgün şekilde almamızı sağlar
from database import SessionLocal
from models import User
from passlib.context import CryptContext
from typing import Annotated
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from fastapi.templating import Jinja2Templates #html ile burayı bağlamak için. HTML css kısımlarındaki değişkenleri buraya aktarmamıza ve templateleri kullanmamızı sağlayan bir sınıf bu.

router = APIRouter(#Daha önceden yaptığımız app = FastAPI() ile aynı ancak farklı dosyalar içeriisndeki bu ifade, http://127.0.0.1:8000/docs kısmında çakışmalara sebep oluyor. Router yapısıyla aslında oop kurallarına uygun farklı dosylaar içerisindeki şeyleri aynı fastapi sayfası içerisinde görebilmemizi sağlıyor. yani eğer burada da bir app=FastAPI() olsa main içerisinde de olsa, python -m uvicorn main:app --reload yazdığımızda main:app dosyasını çalıştırır sadece. router bize hepsini bir yerden çakışma yaşanmadan çalıştırmamızı sağlıyor. artık gidip  main:app yaptığımızda bu routerlar ona ekleyecek hangi sayfada router ile endpoint yaptıysak.
    prefix="/auth", #bütün endpointlerin başına "todoo/" koyacak
    tags=["Authentication"] #http://127.0.0.1:8000/docs sayfası daha okunabilir olsun diye bu sayfadan yapılan endpointleri ayrı bir başlık altında gösterecek
)

templates = Jinja2Templates(directory="templates")

SECRET_KEY = "avw93mm37ylczgipy4br139p472jkvawavw93mm37ylczgipy4br139p472jkvaw"
ALGORITHM = "HS256"


def get_db(): #database'e bağlanma kodu
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)] #database'e get, post, delete, update yapacak olan tüm fonksiyonların get_db, yani database'e bağlanma fonksiyonundan depend etmesini sağlayan satır

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated = "auto") # kullanıcıların parolalarını veritabanında direkt olarak yazdıkları şekliyle tutamayacağımız için, parolaları şifreliyoruz. Burada bcrypt algoritmasıyla şifreleme yapmasını istedik. şifrelenmiş halini aşağıda veritabanına yollayacağız
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token")

class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str
    phone_number: str

class Token(BaseModel):
    access_token: str
    token_type: str

def create_access_token(username:str, userid:int, role:str, expires_delta:timedelta): # tokenin encoding(şifrelenme) kısmı. kullanıcı kayıt olurken ona özel üreteceğimiz token'i yazdığımız fonksiyon
    payload = {'sub': username, 'id':userid, 'role':role}
    expires = datetime.now(timezone.utc) + expires_delta #şu andan itibaren expires_delta süre boyunca geçerli olacak dedik
    payload.update({'exp':expires})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]): # tokenin decoding(şifre çözme) kısmı. user'ın göndermiş olduğu token gerçekten var mı diye kontrol etme. Verify etme. Bunun aslında asıl kullanım yeri todoo.py içerisinde olacak. Atılan isteklerin gerçekten bizim kullanıcılarımız tarafından gelip gelmediğini teyit edebilicez. Örneğin buradaki payload.get('id') sayesinde sadece o id'ye kayıtlı olan todoları gösterebilcez
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # bize gelen payload(token). userdan gelen tokeni al
        username = payload.get('sub') # kullanıcıdan gelen tokenin username'i ne diye bak
        user_id = payload.get('id')
        user_role = payload.get('role')
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Username or ID is invalid")
        return {'username': username, 'id': user_id, 'user_role': user_role}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is invalid")

def authentication_user(username:str, password:str, db): #kullanıcının adı ile databasedeki ad, kullanıcının şifresiyle databasedeki şifre eşleşiyor mu kontrolünün yapıldığı fonksiyon.
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password): #kullanıcının database'de ki encode edilmiş olan şifresiyle parolası örtüşüyor mu diye bak, doğrula
        return False
    return user

# bu iki fonksiyonla aslında front end ile back end fonksiyonlarını birbirine bağlıyoruz. Yani html ve css sayfalarını backend fonksiyonları ile bağlıyoruz
@router.get("/login-page")
def render_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request":request})

@router.get("/register-page")
def render_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request":request})


@router.post("/auth", status_code = status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    user = User(
        username=create_user_request.username,
        email = create_user_request.email,
        first_name = create_user_request.first_name,
        last_name = create_user_request.last_name,
        role = create_user_request.role,
        is_active = True,
        hashed_password = bcrypt_context.hash(create_user_request.password), # kullanıcıların parolalarını bcyrpy algoritmasına göre şifreledik ve öyle database'e yolladık
        phone_number = create_user_request.phone_number
    )
    db.add(user)
    db.commit()



@router.post("/token", response_model = Token) #kullanıcı giriş yaptığında ona bir token(metin) veririz ve o metin gerçekten bir user'a ait bir metin mi, kullanıcı mı giriş yapıyor yoksa bir hacker tarafından mı girilmeye çalışılıyor. herkes kendi todolarını okusun gibi şeyleri kontrol edeceğimiz bir şey olacak bu token
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db:db_dependency):
    user = authentication_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no user such this!")
    token = create_access_token(user.username, user.id, user.role, timedelta(minutes=60))
    return {"access_token":token, "token_type":"bearer"}