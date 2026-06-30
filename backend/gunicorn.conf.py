"""
Gunicorn config for SoccerOctopus backend.

Tournament simulation (104 matches) can take up to 2 minutes in MC mode
and must not be killed by the default 30-second worker timeout.
Nginx proxy_read_timeout is 300s — keep this timeout at or below that.
"""

bind = "127.0.0.1:5002"

# 2 sync workers: enough for normal traffic, avoids memory pressure.
# Increase to 4 on servers with >= 2 GB RAM.
workers = 2
worker_class = "sync"

# Must be < nginx proxy_read_timeout (300s).
# Tournament simulation in MC mode completes in < 30s normally,
# but give headroom for DB lock waits and cold imports.
timeout = 240

keepalive = 5

# Restart workers after N requests to prevent memory leaks from long-running ML jobs.
max_requests = 500
max_requests_jitter = 50

accesslog = "/var/log/gunicorn/socceroctupus.access.log"
errorlog = "/var/log/gunicorn/socceroctupus.error.log"
loglevel = "info"

# Log each request's duration so slow endpoints are visible.
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sus'
