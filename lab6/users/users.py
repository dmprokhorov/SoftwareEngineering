import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from confluent_kafka import Producer
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import List, Optional, Literal
import redis
import json
import os


SECRET_KEY = 'your-secret-key'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ADMIN = 'admin'
PASSWORD = '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/users_db")
engine = create_engine(DATABASE_URL)

REDIS_URL = os.getenv("REDIS_URL", "redis://cache:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
EXPIRE_SECONDS = 300

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

conf = {
    'bootstrap.servers': 'kafka:9092'
}
producer = Producer(**conf)


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

class User(Base):
    __tablename__ = "users"
    login = Column(String(50), index=True, primary_key=True)
    password = Column(String(50), nullable=False)
    name = Column(String(50), index=True)
    surname = Column(String(50), index=True)
    age = Column(Integer, nullable=False)
    email = Column(String(50), nullable=True)


class UserResponse(BaseModel):
    login: str
    password: str
    name: str
    surname: str
    age: Optional[int] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True


Base.metadata.create_all(bind=engine)


def hash(password):
    return pwd_context.hash(password)


pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_client(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Не получается валидировать поля',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        login: str = payload.get('login')
        if login is None:
            raise credentials_exception
        else:
            return login
    except JWTError:
        raise credentials_exception


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expires_delta = expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.utcnow() + expires_delta
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')


def send_message(action: Literal['create', 'update', 'delete'], user_data):
    message = {
        'action': action,
        'data': user_data
    }
    try:
        producer.produce('user_events', value=json.dumps(message), callback=delivery_report)
        producer.flush()
    except Exception as error:
        print(f'error message = {error}')


@app.post("/token", tags=["Основные ручки"])
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    password = PASSWORD if form_data.username == ADMIN else \
        hash(db.query(User).filter(User.login == form_data.username).first().password)
    if pwd_context.verify(form_data.password, password):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={
            'login': form_data.username
        }, expires_delta=access_token_expires)
        return {'access_token': access_token, 'token_type': 'bearer'}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Неправильный логин или пароль',
        headers={"WWW-Authenticate": "Bearer"},
    )


def serialize(user: User) -> dict:
    fields = {}
    for key, value in user.__dict__.items():
        if key != '_sa_instance_state':
            fields[key] = value
    return fields


@app.get("/users", tags=["Основные ручки"], response_model=List[UserResponse])
async def get_users(
        current_user_login: str = Depends(get_current_client),
        db: Session = Depends(get_db)
):
    users = db.query(User).all()
    for user in users:
        cache_login = f'user_login: {user.login}'
        if not redis_client.exists(cache_login):
            redis_client.set(cache_login, json.dumps(serialize(user)), ex=EXPIRE_SECONDS)
        user.password = hash(user.password)
    return users


@app.get("/users/{login}", tags=["Основные ручки"], response_model=UserResponse)
async def get_user_by_login(
        user_login: str, current_user_login: str = Depends(get_current_client),
        db: Session = Depends(get_db)
):
    cache_login = f'user_login: {user_login}'
    if redis_client.exists(cache_login):
        user = redis_client.get(cache_login)
        user = json.loads(user)
    else:
        user = db.query(User).filter(User.login == user_login).first()
        if user is None:
            raise HTTPException(status_code=404, detail='Пользователь не найден')
        redis_client.set(cache_login, json.dumps(serialize(user)), ex=EXPIRE_SECONDS)
    return user


@app.get("/users/get/{name_surname}", tags=["Основные ручки"], response_model=List[UserResponse])
async def get_users_by_name_and_surname(
        user_name: str, user_surname: str,
        current_user: str = Depends(get_current_client),
        db: Session = Depends(get_db)
):
    users = db.query(User).filter(and_(
        User.name == user_name,
        User.surname == user_surname
    )).all()
    if len(users) > 0:
        for user in users:
            cache_login = f'user_login: {user.login}'
            if not redis_client.exists(cache_login):
                redis_client.set(cache_login, json.dumps(serialize(user)), ex=EXPIRE_SECONDS)
            user.password = hash(user.password)
        return users
    raise HTTPException(status_code=404, detail='Пользователи не найдены')


@app.post("/users", tags=["Основные ручки"], response_model=UserResponse)
async def create_user(
        user: UserResponse, current_user_login: str = Depends(get_current_client),
        db: Session = Depends(get_db)
):
    if current_user_login != ADMIN:
        raise HTTPException(status_code=403, detail='Только администратор может создавать новых пользователей')
    if db.query(User).filter(User.login == user.login).first() is not None:
        raise HTTPException(status_code=404, detail='Пользователь уже существует')

    user_data = serialize(user)
    send_message('create', user_data)

    cache_login = f'user_login: {user.login}'
    new_user = User(**user_data)
    redis_client.set(cache_login, json.dumps(serialize(new_user)), ex=EXPIRE_SECONDS)
    return user


@app.delete("/users/{user_login}", tags=["Основные ручки"], response_model=UserResponse)
async def delete_user(
        user_login: str, current_user_login: str = Depends(get_current_client),
        db: Session = Depends(get_db)
):
    if current_user_login not in [ADMIN, user_login]:
        raise HTTPException(status_code=403, detail='Только администратор может удалять других пользователей')
    if (user := db.query(User).filter(User.login == user_login).first()) is None:
        raise HTTPException(status_code=404, detail='Пользователь не найден')

    user_data = serialize(user)
    send_message('delete', user_data)

    cache_login = f'user_login: {user_login}'
    if redis_client.exists(cache_login):
        redis_client.delete(cache_login)
    return user


@app.put("/users/{login}", tags=["Основные ручки"], response_model=UserResponse)
async def update_user(
        user_login: str, updated_user: UserResponse,
        current_user_login: str = Depends(get_current_client),
        db: Session = Depends(get_db)
):
    if current_user_login not in [ADMIN, user_login]:
        raise HTTPException(status_code=403, detail='Только администратор может изменять других пользователей')
    potential = db.query(User).filter(User.login == user_login)
    if potential.first() is None:
        raise HTTPException(status_code=404, detail='Пользователь не найден')
    if user_login != updated_user.login and \
            db.query(User).filter(User.login == updated_user.login).first() is not None:
        raise HTTPException(status_code=403, detail='Пользователь с новым логином уже существует')

    user_data = serialize(updated_user)
    user_data['old_login'] = user_login
    send_message('update', user_data)

    redis_client.delete(f'user_login: {user_login}')
    redis_client.set(f'user_login: {updated_user.login}', json.dumps(user_data), ex=EXPIRE_SECONDS)
    return updated_user


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000, reload=True)