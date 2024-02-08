FROM python:3.12-alpine

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
# This step can be optional if your bot doesn't serve HTTP traffic
# EXPOSE 80

# Define environment variable
ENV DISCORD_BOT_TOKEN=""
ENV CHATGPT_API_KEY=""

# Run bot.py when the container launches
CMD ["python", "bot.py"]
