FROM python:3.8

WORKDIR /app

COPY . /app

CMD ["python", "main.py", "sandbox/a", "sandbox/b", "sandbox/c"]
