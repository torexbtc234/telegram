# Use official Python 3.11 image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy repo files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (Deployra uses $PORT)
ENV PORT=8000
EXPOSE $PORT

# Run the bot
CMD ["python", "websocket_bot.py"]
