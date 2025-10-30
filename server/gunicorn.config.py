import os

bind = f"0.0.0.0:{os.environ.get('PACKIT_HANDLER_PORT', 8090)}"
worker_class = "uvicorn.workers.UvicornWorker"
workers = 2
# timeout set to 600 seconds; with 32 clusters and several runs in parallel, it
# can take even 10 minutes for a query to complete
timeout = 600
# write to stdout
accesslog = "-"
