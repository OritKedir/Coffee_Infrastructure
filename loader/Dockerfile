# 1. Use an official lightweight Python image
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy and install dependencies first (leverages Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the loader script into the container
COPY load_data.py .

# 5. Specify the default command to execute on startup
CMD ["python", "load_data.py"]