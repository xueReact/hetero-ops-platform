FROM python:3.12-slim
WORKDIR /app
COPY platform_app ./platform_app
COPY sample_data ./sample_data
COPY web ./web
COPY simulations/airport-upgrade/site ./simulations/airport-upgrade/site
COPY run.py ./run.py
ENV FIRE_HOST=0.0.0.0 FIRE_PORT=8000 FIRE_OPEN_BROWSER=0 PYTHONUNBUFFERED=1
ENV FIRE_RUNTIME_DATA_DIR=/data
EXPOSE 8000
CMD ["python", "run.py"]
