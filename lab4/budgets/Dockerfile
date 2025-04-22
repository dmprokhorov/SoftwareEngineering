FROM python:3.12.6

WORKDIR /app

COPY ./budgets/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./budgets/budgets.py .
COPY ./budgets/fill.py .

CMD bash -c "python fill.py && uvicorn budgets:app --host 0.0.0.0 --port 8001"