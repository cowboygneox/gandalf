FROM python:3
RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app
RUN pip install -r requirements.txt
ADD ./app /app/app
ADD run.py /app
CMD ["python", "-u", "run.py"]
