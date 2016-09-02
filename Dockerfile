FROM python:3-alpine
RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app
RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev
RUN pip install -r requirements.txt
COPY ./app /app/app
RUN find . -name \*.pyc -delete
ADD run.py /app
CMD ["python", "-u", "run.py"]
