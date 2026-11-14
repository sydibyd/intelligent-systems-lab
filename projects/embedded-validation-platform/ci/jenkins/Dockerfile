FROM python:3.11-slim-trixie AS python-runtime

FROM jenkins/jenkins:lts-jdk21

USER root

COPY --from=python-runtime /usr/local/ /usr/local/

RUN ldconfig \
    && python3 --version \
    && python3 -m pip --version \
    && python3 -m venv /tmp/python-check \
    && /tmp/python-check/bin/python --version \
    && rm -rf /tmp/python-check

USER jenkins
