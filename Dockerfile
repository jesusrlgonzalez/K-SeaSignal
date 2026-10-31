FROM python:3.11-slim
WORKDIR /work
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/work/src
USER 65534:65534
CMD ["python", "-m", "pytest", "-q"]
# Dockerfile prepared only; no container build performed.
