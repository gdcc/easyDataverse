FROM python:3.9

WORKDIR /app

ADD . /app

RUN python3 -m pip install --no-cache-dir --upgrade -r requirements.txt
RUN python3 -m pip install . --no-cache-dir

COPY ./pyExampleAPI/pyexampleapi_server.py /app

CMD ["uvicorn", "pyexampleapi_server:app", "--host", "0.0.0.0", "--port", "80"]