import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import List, Optional


SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ADMIN = 'admin'


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class User(BaseModel):
    login: str
    password: str
    name: str
    surname: str
    age: int | None = Field(ge=0)
    email: str | None = EmailStr


def get_initials(name: str, surname: str) -> str:
    return name + ', ' + surname


def hash(password):
    return pwd_context.hash(password)


pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')


users_db, initials = {}, {}
client_db = {
    ADMIN:  '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'
}


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


@app.post("/token", tags=["Основные ручки"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username in client_db and \
        pwd_context.verify(form_data.password, client_db[form_data.username]):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={'login': form_data.username}, expires_delta=access_token_expires)
        return {'access_token': access_token, 'token_type': 'bearer'}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Неправильный логин или пароль',
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.get("/users", tags=["Основные ручки"], response_model=List[User])
def get_users(current_user_login: str = Depends(get_current_client)):
    users = list(users_db.values()).copy()
    for user in users:
        user.password = hash(user.password)
    return users


@app.get("/users/{login}", tags=["Основные ручки"], response_model=User)
def get_user_by_login(user_login: str, current_user_login: str = Depends(get_current_client)):
    if user_login in users_db:
        user = users_db[user_login].copy()
        user.password = hash(user.password)
        return user
    raise HTTPException(status_code=404, detail='Пользователь не найден')


@app.get("/users/get/{name_surname}", tags=["Основные ручки"], response_model=List[User])
def get_users_by_name_and_surname(user_name: str, user_surname: str, current_user: str = Depends(get_current_client)):
    user_initials = get_initials(user_name, user_surname)
    if user_initials not in initials:
        raise HTTPException(status_code=404, detail='Пользователь не найден')
    users = [users_db[user_id] for user_id in initials[user_initials]]
    for user in users:
        user.password = hash(user.password)
    return users


@app.post("/users", tags=["Основные ручки"], response_model=User)
def create_user(user: User, current_user_login: str = Depends(get_current_client), renew=False):
    if current_user_login != 'admin' and not renew:
        raise HTTPException(status_code=403, detail='Только администратор может создавать новых пользователей')
    if user.login in users_db:
        raise HTTPException(status_code=404, detail='Пользователь уже существует')
    users_db[user.login] = user
    user_initials = get_initials(user.name, user.surname)
    if user_initials not in initials:
        initials[user_initials] = set()
    initials[user_initials].add(user.login)
    client_db[user.login] = hash(user.password)
    return user


@app.delete("/users/{user_login}", tags=["Основные ручки"], response_model=User)
def delete_user(user_login: str, current_user_login: str = Depends(get_current_client)):
    if current_user_login != 'admin' and current_user_login != user_login:
        raise HTTPException(status_code=403, detail='Только администратор может удалять других пользователей')
    if user_login not in users_db:
        raise HTTPException(status_code=404, detail='Пользователь не найден')
    user = users_db[user_login]
    user_initials = get_initials(user.name, user.surname)
    initials[user_initials].remove(user_login)
    if len(initials[user_initials]) == 0:
        initials.pop(user_initials)
    users_db.pop(user_login)
    client_db.pop(user_login)
    return user


@app.put("/users/{login}", tags=["Основные ручки"], response_model=User)
def update_user(user_login: str, updated_user: User, current_user_login: str = Depends(get_current_client)):
    if current_user_login != 'admin' and current_user_login != user_login:
        raise HTTPException(status_code=403, detail='Только администратор может изменять других пользователей')
    if user_login not in users_db:
        raise HTTPException(status_code=404, detail='Пользователь не найден')
    if updated_user.login in users_db:
        raise HTTPException(status_code=403, detail='Пользователь с новым логином уже существует')
    delete_user(user_login, current_user_login)
    create_user(updated_user, current_user_login, renew=True)
    return updated_user


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000, reload=True)