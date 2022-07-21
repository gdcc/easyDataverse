FROM python:3.9

WORKDIR /app

ADD . /app

RUN python3 -m pip install --no-cache-dir --upgrade -r requirements.txt
RUN python3 -m pip install . --no-cache-dir

COPY ./pySomeTest/pysometest_server.py /app

CMD ["uvicorn", "pysometest_server:app", "--host", "0.0.0.0", "--port", "80"]