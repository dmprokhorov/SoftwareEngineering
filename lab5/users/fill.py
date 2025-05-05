from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from users import User, Base, hash, pwd_context
import os


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/users_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def fill_data():
    db = SessionLocal()

    try:
        if db.query(User).count() > 0:
            print("База данных уже содержит пользователей. Пропускаем заполнение")
            return

        users = [
            User(
                login='andreyka',
                password='abc12345',
                name="Andrey",
                surname="Andreev",
                age=44,
                email="andreyka@google.com"
            ),
            User(
                login='elderson',
                password='zaq1xsw2',
                name='Andrey',
                surname='Andreev',
                age=26,
                email="elder@yandex.ru"
            ),
            User(
                login='Pitro',
                password='abracadabra',
                name='Peter',
                surname='Petrov',
                age=32,
                email="joker92@google.com"
            )
        ]

        db.add_all(users)
        db.commit()
        print("База данных успешно заполнена тестовыми пользователями")

    except Exception as e:
        db.rollback()
        print(f"Произошла ошибка при заполнении базы данных: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    fill_data()