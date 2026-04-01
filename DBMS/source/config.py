import os

MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "Parthiban2006@06"
MYSQL_DATABASE = "Voidlocker"

SECRET_KEY = "digilocker-secret-key-change-in-production"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "..", "uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

CATEGORIES = [
    "Aadhaar",
    "PAN",
    "Marksheet",
    "Driving License",
    "Passport",
    "Certificate",
    "Other"
]

ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx',
    'xls', 'xlsx', 'txt', 'csv', 'ppt', 'pptx'
}
