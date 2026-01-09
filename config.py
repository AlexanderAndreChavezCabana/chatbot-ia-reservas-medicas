from dotenv import load_dotenv
import os

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "ReservasMedicas")
DEBUG = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
