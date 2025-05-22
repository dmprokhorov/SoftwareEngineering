import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import date, datetime
import os

MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://root:password@mongodb:27017/')
client = AsyncIOMotorClient(MONGODB_URL)
db = client['budget_db']
incomes_collection = db['incomes']
outcomes_collection = db['outcomes']


async def fill_data():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client['budget_db']
    incomes_collection = db['incomes']
    outcomes_collection = db['outcomes']

    count_incomes = await incomes_collection.count_documents({})
    count_outcomes = await outcomes_collection.count_documents({})
    if count_incomes > 0 or count_outcomes > 0:
        print('Коллекции уже содержат данные. Заполнение тестовыми данными пропущено.')
        return

    test_data = [
        (incomes_collection, "elderson", 990, date(2023, 4, 10)),
        (incomes_collection, "elderson", 1450, date(2023, 4, 17)),
        (incomes_collection, "elderson", 2200, date(2023, 4, 20)),
        (incomes_collection, "elderson", 130, date(2023, 4, 21)),
        (incomes_collection, "andreyka", 660, date(2023, 4, 10)),
        (incomes_collection, "andreyka", 540, date(2023, 4, 19)),
        (incomes_collection, "Pitro", 890, date(2023, 4, 12)),
        (incomes_collection, "Pitro", 980, date(2023, 4, 13)),
        (incomes_collection, "Pitro", 110, date(2023, 4, 22)),
        (outcomes_collection, "elderson", 500, date(2023, 4, 6)),
        (outcomes_collection, "elderson", 330, date(2023, 4, 14)),
        (outcomes_collection, "andreyka", 1920, date(2023, 4, 20)),
        (outcomes_collection, "andreyka", 500, date(2023, 4, 13)),
        (outcomes_collection, "andreyka", 300, date(2023, 4, 15)),
        (outcomes_collection, "Pitro", 800, date(2023, 4, 10)),
        (outcomes_collection, "Pitro", 500, date(2023, 4, 11)),
        (outcomes_collection, "Pitro", 300, date(2023, 4, 17))
    ]

    for collection, user, sum, dt in test_data:
        await collection.insert_one({
            'user_login': user,
            'sum': sum,
            'date': datetime(dt.year, dt.month, dt.day)
        })

    print('Тестовые данные успешно добавлены')

if __name__ == "__main__":
    asyncio.run(fill_data())