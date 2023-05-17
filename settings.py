import os
from dotenv import load_dotenv

load_dotenv("./.env")
SECRET_KEY = os.environ.get("APP_SECRET_KEY")
MY_EMAIL = os.environ.get("EMAIL")
EMAIL_KEY = os.environ.get("EMAIL_KEY")
