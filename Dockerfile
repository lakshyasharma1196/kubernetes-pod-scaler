FROM python:3.9

COPY scale.py /scale.py

RUN pip install kubernetes

CMD ["python", "scale.py"]
