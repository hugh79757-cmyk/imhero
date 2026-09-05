import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]

@dataclass
class Settings:
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"

    NAVER_CLIENT_ID: str = field(default_factory=lambda: os.getenv("NAVER_CLIENT_ID",""))
    NAVER_CLIENT_SECRET: str = field(default_factory=lambda: os.getenv("NAVER_CLIENT_SECRET",""))
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY",""))
    NVIDIA_API_KEY: str = field(default_factory=lambda: os.getenv("NVIDIA_API_KEY",""))
    NVIDIA_BASE_URL: str = field(default_factory=lambda: os.getenv("NVIDIA_BASE_URL","https://integrate.api.nvidia.com/v1"))
    TISTORY_EMAIL: str = field(default_factory=lambda: os.getenv("TISTORY_EMAIL",""))
    TISTORY_PASSWORD: str = field(default_factory=lambda: os.getenv("TISTORY_PASSWORD",""))
    TISTORY_BLOG_URL: str = field(default_factory=lambda: os.getenv("TISTORY_BLOG_URL","https://youaremyhero.tistory.com"))
    YOUTUBE_API_KEY: str = field(default_factory=lambda: os.getenv("YOUTUBE_API_KEY",""))

    def validate(self):
        errs=[]
        if not self.NAVER_CLIENT_ID: errs.append("NAVER_CLIENT_ID")
        if not self.NAVER_CLIENT_SECRET: errs.append("NAVER_CLIENT_SECRET")
        return errs
