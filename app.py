from run import app

# Vercel and other WSGI hosts expect an "app" object in a top‑level module.
# run.py already constructs the application via create_app(), so we simply
# import it here. No need for a __main__ block.  
