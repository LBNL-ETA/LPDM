FROM python:2.7

COPY requirements.txt /tmp/
RUN pip install --requirement /tmp/requirements.txt
# not sure why but paramiko doesn't install via pip
#RUN easy_install paramiko

RUN mkdir /LPDM
WORKDIR /LPDM
CMD ["python", "run_scenarios.py"]
