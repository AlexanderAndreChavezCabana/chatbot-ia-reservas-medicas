from dotenv import load_dotenv
import os
import os as _os

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "ReservasMedicas")
DEBUG = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")
DATA_DIR = os.getenv("DATA_DIR", _os.path.join(_os.path.dirname(__file__), "data"))
