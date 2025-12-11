import os
import sys

if '-h' in sys.argv or '--help' in sys.argv:
    with open("help.txt", 'r') as f:
        print(f.read())
        sys.exit(0)

# if the environment variable HEADLESS is 1, we run headless mode
if os.environ.get("HEADLESS") == "1":
    from src.headless_main import run_headless

    run_headless()

# otherwise we run GUI based mode
else:
    from src import app

    app.main(sys.argv)
