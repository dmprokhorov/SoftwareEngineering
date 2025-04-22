import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING
from pydantic import BaseModel
from datetime import date, datetime
from jose import JWTError, jwt
from typing import List
import os
import asyncio


SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ADMIN = 'admin'


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='http://127.0.0.1:8000/token')


app = FastAPI()


MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://root:password@mongodb:27017/')
client = AsyncIOMotorClient(MONGODB_URL)
db = client['budget_db']
incomes_collection = db['incomes']
outcomes_collection = db['outcomes']


async def create_indexes():
    await incomes_collection.create_indexes([
        IndexModel(
            [('user_login', ASCENDING), ('date', ASCENDING)]
        )
    ])

    await outcomes_collection.create_indexes([
        IndexModel(
            [('user_login', ASCENDING), ('date', ASCENDING)]
        )
    ])


@app.on_event('startup')
async def startup_db():
    await create_indexes()
    print('Indexes created successfully')


class Budget(BaseModel):
    user_login: str
    sum: int
    date: date


def convert(date):
    return datetime(
        year=date.year,
        month=date.month,
        day=date.day
    )


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


@app.get("/all_incomes/", tags=["Основные ручки"], response_model=List[Budget])
async def get_all_incomes(current_user_login: str = Depends(get_current_client)):
    if current_user_login == ADMIN:
        cursor = await incomes_collection.find().sort('date', ASCENDING).to_list()
        return [Budget(**income) for income in cursor]
    raise HTTPException(status_code=403, detail='Только администратор может просматривать все доходы')


@app.get("/all_outcomes/", tags=["Основные ручки"], response_model=List[Budget])
async def get_all_outcomes(current_user_login: str = Depends(get_current_client)):
    if current_user_login == ADMIN:
        cursor = await outcomes_collection.find().sort('date', ASCENDING).to_list()
        return [Budget(**outcome) for outcome in cursor]
    raise HTTPException(status_code=403, detail='Только администратор может просматривать все расходы')


@app.get("/incomes/{user_login}", tags=["Основные ручки"], response_model=List[Budget])
async def get_incomes(
    user_login: str,
    current_user_login: str = Depends(get_current_client)
):
    if current_user_login in [user_login, ADMIN]:
        cursor = await incomes_collection.find({'user_login': user_login}).sort('date', ASCENDING).to_list()
        return [Budget(**income) for income in cursor]
    raise HTTPException(status_code=403, detail='Неадминистрированный пользователь может просматривать только свои доходы')


@app.get("/outcomes/{user_login}", tags=["Основные ручки"], response_model=List[Budget])
async def get_outcomes(
    user_login: str,
    current_user_login: str = Depends(get_current_client)
):
    if current_user_login in [user_login, ADMIN]:
        cursor = await outcomes_collection.find({'user_login': user_login}).sort('date', ASCENDING).to_list()
        return [Budget(**outcome) for outcome in cursor]
    raise HTTPException(status_code=403, detail='Неадминистрированный пользователь может просматривать только свои расходы')


@app.post("/incomes/{user_login}", tags=["Основные ручки"], response_model=Budget)
async def create_income(
    budget: Budget,
    current_user_login: str = Depends(get_current_client)
):
    if current_user_login in [budget.user_login, ADMIN]:
        budget.date = convert(budget.date)
        previous = await incomes_collection.find_one({'user_login': budget.user_login, 'date': budget.date})
        if previous:
            await incomes_collection.update_one(
                {'user_login': budget.user_login, 'date': budget.date},
                {'$set': {'sum': budget.sum + previous['sum']}}
            )
            budget.sum += previous['sum']
        else:
            await incomes_collection.insert_one(budget.model_dump())
        return budget
    raise HTTPException(status_code=403, detail='Неадминистрированный пользователь может создавать только свои доходы')


@app.post("/outcomes/{user_login}", tags=["Основные ручки"], response_model=Budget)
async def create_outcome(
    budget: Budget,
    current_user_login: str = Depends(get_current_client)
):
    if current_user_login in [budget.user_login, ADMIN]:
        budget.date = convert(budget.date)
        previous = await outcomes_collection.find_one({'user_login': budget.user_login, 'date': budget.date})
        if previous:
            await outcomes_collection.update_one(
                {'user_login': budget.user_login, 'date': budget.date},
                {'$set': {'sum': budget.sum + previous['sum']}}
            )
            budget.sum += previous['sum']
        else:
            await outcomes_collection.insert_one(budget.model_dump())
        return budget
    raise HTTPException(status_code=403, detail='Неадминистрированный пользователь может создавать только свои расходы')


@app.put("/incomes/{user_login}", tags=["Основные ручки"], response_model=Budget)
async def update_income(
        updated_budget: Budget,
        current_user_login: str = Depends(get_current_client)
):
    if current_user_login in [updated_budget.user_login, ADMIN]:
        updated_budget.date = convert(updated_budget.date)
        previous = await incomes_collection.find_one({'user_login': updated_budget.user_login, 'date': updated_budget.date})
        if previous:
            await incomes_collection.update_one(
                {'user_login': updated_budget.user_login, 'date': updated_budget.date},
                {'$set': {'sum': updated_budget.sum}}
            )
            return updated_budget
        raise HTTPException(status_code=404, detail='У данного пользователя нет дохода в данный день')
    raise HTTPException(status_code=403, detail='Неадминистрированный пользователь может изменять только свои доходы')


@app.put("/outcomes/{user_login}", tags=["Основные ручки"], response_model=Budget)
async def update_outcome(
        updated_budget: Budget,
        current_user_login: str = Depends(get_current_client)
):
    if current_user_login in [updated_budget.user_login, ADMIN]:
        updated_budget.date = convert(updated_budget.date)
        previous = await outcomes_collection.find_one({'user_login': updated_budget.user_login, 'date': updated_budget.date})
        if previous:
            await outcomes_collection.update_one(
                {'user_login': updated_budget.user_login, 'date': updated_budget.date},
                {'$set': {'sum': updated_budget.sum}}
            )
            return updated_budget
        raise HTTPException(status_code=404, detail='У данного пользователя нет расхода в данный день')
    raise HTTPException(status_code=403, detail='Неадминистрированный пользователь может изменять только свои расходы')


@app.delete("/incomes/{user_login}", tags=["Основные ручки"], response_model=Budget)
async def delete_income(user_login: str, date: date, current_user_login: str = Depends(get_current_client)):
    if current_user_login in [user_login, ADMIN]:
        date = convert(date)
        previous = await incomes_collection.find_one({'user_login': user_login, 'date': date})
        if previous:
            sum = previous['sum']
            await incomes_collection.delete_one(
                {'user_login': user_login, 'date': date}
            )
            return Budget(user_login=user_login, date=date, sum=sum)
        raise HTTPException(status_code=404, detail='У данного пользователя нет дохода в данный день')
    raise HTTPException(status_code=403, detail='Неадминистрированный пользователь может удалять только свои доходы')


@app.delete("/outcomes/{user_login}", tags=["Основные ручки"], response_model=Budget)
async def delete_outcome(user_login: str, date: date, current_user_login: str = Depends(get_current_client)):
    if current_user_login in [user_login, ADMIN]:
        date = convert(date)
        previous = await outcomes_collection.find_one({'user_login': user_login, 'date': date})
        if previous:
            sum = previous['sum']
            await outcomes_collection.delete_one(
                {'user_login': user_login, 'date': date}
            )
            return Budget(user_login=user_login, date=date, sum=sum)
        raise HTTPException(status_code=404, detail='У данного пользователя нет расхода в данный день')
    raise HTTPException(status_code=403, detail='Неадминистрированный пользователь может удалять только свои расходы')


@app.get("/dynamic/{user_login}", tags=["Основные ручки"])
async def get_dynamic(
        user_login: str,
        first_date: date, last_date: date,
        current_user_login: str = Depends(get_current_client)
):
    if current_user_login in [ADMIN, user_login]:
        sum = 0
        first_date = convert(first_date)
        last_date = convert(last_date)
        needed_incomes = await incomes_collection.find({
            'user_login': user_login,
            'date':
                {'$gte': first_date, '$lte': last_date}
        }).to_list()
        for item in needed_incomes:
            sum += item['sum']
        needed_outcomes = await outcomes_collection.find({
            'user_login': user_login,
            'date':
                {'$gte': first_date, '$lte': last_date}
        }).to_list()
        for item in needed_outcomes:
            sum -= item['sum']
        return sum
    raise HTTPException(
        status_code=403,
        detail='Неавторизованный пользователь может считать динамику только по своим данным'
    )


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8001, reload=True)