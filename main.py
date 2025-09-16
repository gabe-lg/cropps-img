import os

# if the environment variable HEADLESS is 1, we run headless mode
if os.environ.get("HEADLESS") == "1":
    from src.headless_main import run_headless
    run_headless()

# otherwise we run GUI based mode
else:
    from src import app
    app.main()
