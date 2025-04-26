from database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey


class Todo(Base):
    __tablename__ = 'todos' #bu Base için bir special property'dir. Bunu yazmamız gerekli. Aslında database'in table'ının adı

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    priority = Column(Integer)
    complete = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey('users.id')) #users tablosuyla bu tablo arasında ilişkisel bir bağlantı kurduk. yani herkes kendi todosonu görebilecek sadece. bu todonun sahibi, aşağıdaki user, başkası değil. Table'lar arası relationship kurduk. Bunun adı da ilişkisel veritabalı
    #Şu anda 5 tane sütun oluşturduk ve bu sütunların hangi türde veritipi(string, int) alacağını belirledik. Bunlar id, title, description, priority ve complete isimli Columnlardır.

#halihazırda db içerisinde aktif bulunan bir tablo içerisine bir column eklersek bu column eklenmez. sonradan eklendiği için önceden girilen değerler için hangi değerler alacağını bilemediğinden böyle bir şeyi migrigation ile yapmalıyız
# Migrigation

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key = True, index = True)
    email = Column(String, unique=True)
    username = Column(String, unique=True)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String)
    phone_number = Column(String) # migrigation yapmayı öğrenmek için sonradan ekledik bunu