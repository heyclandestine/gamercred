import multiprocessing
import os

# Server socket
bind = "0.0.0.0:" + str(os.getenv("PORT", "10000"))
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'gamercred'

# SSL
keyfile = None
certfile = None

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Static files
static_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'website', 'public') 