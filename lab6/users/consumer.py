from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from confluent_kafka import Consumer, KafkaException
from users import User, Base
import json
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@postgres:5432/users_db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka:9092')
GROUP_ID = 'my_group'


def process_message(db, message):
    try:
        msg_value = json.loads(message.value().decode('utf-8'))
        action = msg_value['action']
        data = msg_value['data']

        if action == 'create':
            new_user = User(
                login=data['login'],
                password=data['password'],
                name=data['name'],
                surname=data['surname'],
                age=data['age'],
                email=data.get('email')
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

        elif action == 'update':
            potential = db.query(User).filter(User.login == data['old_login'])
            potential.update({
                'login': data['login'],
                'password': data['password'],
                'name': data['name'],
                'surname': data['surname'],
                'age': data['age'],
                'email': data['email']
            })
            db.commit()

        elif action == 'delete':
            user = db.query(User).filter(User.login == data['login']).first()
            db.delete(user)
            db.commit()

    except Exception as e:
        logger.error(f'Error processing message: {str(e)}')
        db.rollback()


def consume_messages():
    Base.metadata.create_all(bind=engine)

    consumer_config = {
        'bootstrap.servers': KAFKA_BROKER,
        'group.id': GROUP_ID,
        'auto.offset.reset': 'earliest'
    }

    consumer = Consumer(consumer_config)
    consumer.subscribe(['user_events'])

    db = SessionLocal()

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if error := msg.error():
                print(error.code())
                if error.code() == 3:
                    continue
                raise KafkaException(error)
            process_message(db, msg)

    except Exception as error:
        print(f'Error occurred: {error}')
    finally:
        consumer.close()


if __name__ == '__main__':
    consume_messages()