FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements (needed for Streamlit UI but kept for completeness)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Run the CLI batch processor by default instead of the UI
CMD ["python", "main.py"]
