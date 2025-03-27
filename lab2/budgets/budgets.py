import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import date
from jose import JWTError, jwt
from typing import List


SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ADMIN = 'admin'


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='http://127.0.0.1:8000/token')


app = FastAPI()


class Budget(BaseModel):
    id: int
    user_login: str
    sum: int
    date: date


incomes, outcomes = {}, {}


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


@app.get("/incomes", tags=["Основные ручки"], response_model=List[Budget])
def get_incomes(current_user_login: str = Depends(get_current_client)):
    if current_user_login == ADMIN:
        return list(incomes.values())
    raise HTTPException(status_code=403, detail='Только администратор может просматривать все доходы')


@app.get("/outcomes", tags=["Основные ручки"], response_model=List[Budget])
def get_outcomes(current_user_login: str = Depends(get_current_client)):
    if current_user_login == ADMIN:
        return list(outcomes.values())
    raise HTTPException(status_code=403, detail='Только администратор может просматривать все траты')


def get_budget(
        budget_id: int, storage: dict, detail1: str, detail2: str,
        current_user_login: str = Depends(get_current_client)
):
    if budget_id in storage:
        if current_user_login in [ADMIN, storage[budget_id].user_login]:
            return storage[budget_id]
        raise HTTPException(status_code=403, detail=detail2)
    raise HTTPException(status_code=404, detail=detail1)


@app.get("/incomes/{income_id}", tags=["Основные ручки"], response_model=Budget)
def get_income(income_id: int, current_user_login: str = Depends(get_current_client)):
    return get_budget(
        income_id, incomes, 'Нужный доход не найден',
        'Только администратор может просматривать чужие доходы',
        current_user_login
    )


@app.get("/outcomes/{outcome_id}", tags=["Основные ручки"], response_model=Budget)
def get_outcome(outcome_id: int, current_user_login: str = Depends(get_current_client)):
    return get_budget(
        outcome_id, outcomes, 'Нужные траты не найдены',
        'Только администратор может просматривать чужие траты',
        current_user_login
    )


def create_budget(
        storage: dict, budget: Budget, detail1: str, detail2: str,
        current_user_login: str = Depends(get_current_client),
        renew=False
):
    if budget.id not in storage:
        if renew or current_user_login in [ADMIN, budget.user_login]:
            storage[budget.id] = budget
            return budget
        raise HTTPException(status_code=403, detail=detail2)
    raise HTTPException(status_code=404, detail=detail1)


@app.post("/incomes/{income_id}", tags=["Основные ручки"], response_model=Budget)
def create_income(budget: Budget, current_user_login: str = Depends(get_current_client)):
    return create_budget(
        incomes, budget, 'Нужный доход уже существует',
        'Неадминистрированный пользователь не может создать доход другому пользователю',
        current_user_login
    )


@app.post("/outcomes/{outcome_id}", tags=["Основные ручки"], response_model=Budget)
def create_outcome(budget: Budget, current_user_login: str = Depends(get_current_client)):
    return create_budget(
        outcomes, budget, 'Нужные траты уже существуют',
        'Неадминистрированный пользователь не может создать траты другому пользователю',
        current_user_login
    )


def delete_budget(
        budget_id: int, storage: dict, detail1: str, detail2: str,
        current_user_login: str = Depends(get_current_client)
):
    if budget_id in storage:
        if current_user_login in [ADMIN, storage[budget_id].user_login]:
            return storage.pop(budget_id)
        raise HTTPException(status_code=403, detail=detail2)
    raise HTTPException(status_code=404, detail=detail1)


@app.delete("/incomes/{income_id}", tags=["Основные ручки"], response_model=Budget)
def delete_income(income_id: int, current_user_login: str = Depends(get_current_client)):
    return delete_budget(
        income_id, incomes, 'Нужный доход не найден',
        'Неадминистрированный пользователь не может удалять чужой доход',
        current_user_login
    )


@app.delete("/outcomes/{outcome_id}", tags=["Основные ручки"], response_model=Budget)
def delete_outcome(outcome_id: int, current_user_login: str = Depends(get_current_client)):
    return delete_budget(
        outcome_id, outcomes, 'Нужные траты не найдены',
        'Неадминистрированный пользователь не может удалять чужие траты',
        current_user_login
    )


def update_budget(
        budget_id: int, storage: dict, updated_budget: Budget,
        detail1: str, detail2: str, current_user_login: str = Depends(get_current_client)
):
    if budget_id in storage:
        if updated_budget.id == budget_id or updated_budget.id != budget_id and \
                updated_budget.id not in storage:
            delete_budget(budget_id, storage, detail1, detail2, current_user_login)
            create_budget(storage, updated_budget, detail2, current_user_login, detail2, True)
            return updated_budget
        raise HTTPException(status_code=403, detail=detail2)
    raise HTTPException(status_code=404, detail=detail1)


@app.put("/incomes/{income_id}", tags=["Основные ручки"], response_model=Budget)
def update_income(
        income_id: int, updated_income: Budget,
        current_user_login: str = Depends(get_current_client)
):
    return update_budget(
        income_id, incomes, updated_income,
        'Нужный доход не найден',
        'Доход с новым идентификатором уже существует',
        current_user_login
    )


@app.put("/outcomes/{outcome_id}", tags=["Основные ручки"], response_model=Budget)
def update_outcome(
        outcome_id: int, updated_outcome: Budget,
        current_user_login: str = Depends(get_current_client)
):
    return update_budget(
        outcome_id, outcomes, updated_outcome,
        'Нужные траты не найдены',
        'Траты с новым идентификатором уже существуют',
        current_user_login
    )


@app.get("/dynamic/{user_login}", tags=["Основные ручки"])
def get_dynamic(
        user_login: str,
        first_date: date, last_date: date,
        current_user_login: str = Depends(get_current_client)
):
    if current_user_login in [ADMIN, user_login]:
        sum = 0
        for income in incomes.values():
            if current_user_login in [ADMIN, income.user_login] and \
                first_date <= income.date <= last_date:
                sum += income.sum
        for outcome in outcomes.values():
            if current_user_login in [ADMIN, outcome.user_login] and \
                first_date <= outcome.date <= last_date:
                sum -= outcome.sum
        return sum
    raise HTTPException(
        status_code=403,
        detail='Неавторизованный пользователь может считать динамику только по своим данным'
    )


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8001, reload=True)