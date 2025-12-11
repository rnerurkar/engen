FROM python:3.10-slim

WORKDIR /app

# Copy shared library
COPY ./lib /app/lib
ENV PYTHONPATH=/app/lib

# Install Agent dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Agent Code
COPY main.py .

# Run
CMD ["python", "main.py"]