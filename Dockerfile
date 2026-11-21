FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

WORKDIR /app
COPY src/selector.py src/coverage_map.json.gz ./
RUN chmod 0444 /app/selector.py /app/coverage_map.json.gz

USER 65534:65534
CMD ["python", "/app/selector.py"]
