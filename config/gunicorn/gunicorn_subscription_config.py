# gunicorn_config.py

bind = "0.0.0.0:5440"  # Bind to all IP addresses on port 5440
workers = 4            # Number of worker processes
threads = 2            # Number of threads per worker
timeout = 120          # Request timeout in seconds
