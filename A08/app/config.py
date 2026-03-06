import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # 数据库配置
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")
    DB_NAME = os.getenv("DB_NAME", "energy_management")

    # 数据库连接URL
    DATABASE_URL = f"mysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # 应用配置
    APP_NAME = os.getenv("APP_NAME", "建筑能源管理系统")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"


config = Config()