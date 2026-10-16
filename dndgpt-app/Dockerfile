FROM python:3.12-slim
WORKDIR /srv/dndgpt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home dndgpt && mkdir /data && chown dndgpt /data
COPY app ./app
COPY rules ./rules
USER dndgpt
ENV DNDGPT_ENV=production DNDGPT_DB=/data/campaigns.sqlite3 PYTHONDONTWRITEBYTECODE=1
VOLUME /data
EXPOSE 8765
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8765"]
