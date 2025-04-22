FROM python:3.12.6

WORKDIR /app

COPY ./users/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./users/users.py .
COPY ./users/fill.py .

CMD bash -c "python fill.py && uvicorn users:app --host 0.0.0.0 --port 8000"