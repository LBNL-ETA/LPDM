FROM python:2.7

COPY requirements.txt /tmp/
RUN pip install --requirement /tmp/requirements.txt

RUN mkdir /LPDM
WORKDIR /LPDM
CMD ["python", "run_scenarios.py"]
