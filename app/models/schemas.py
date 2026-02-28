from typing import List, Optional
from pydantic import BaseModel
from app.core.config import get_kindle_folder

class BookModel(BaseModel):
    id: int
    title: str
    author: str
    file_path: str
    file_type: str
    cover_path: Optional[str] = None
    added_date: Optional[str] = None
    series: Optional[str] = None
    volume: Optional[float] = None
    synopsis: Optional[str] = None
    publisher: Optional[str] = None
    publish_year: Optional[int] = None

class SendBookRequest(BaseModel):
    id: int
    kindle_path: str = ""

class UpdateBookRequest(BaseModel):
    title: str
    author: str
    series: Optional[str] = None
    volume: Optional[float] = None
    synopsis: Optional[str] = None
    publisher: Optional[str] = None
    publish_year: Optional[int] = None

class DeleteBookRequest(BaseModel):
    ids: List[int]
    permanent: bool = False

class DownloadCoverRequest(BaseModel):
    url: str

class SettingsRequest(BaseModel):
    books_folder: str
    scanner_threads: int = 2

class ProfileModel(BaseModel):
    id: int
    name: str
    avatar: Optional[str] = None

class ProfileCreateRequest(BaseModel):
    name: str
    avatar: Optional[str] = None

class ReadingProgressModel(BaseModel):
    id: int
    profile_id: int
    book_id: int
    cfi_location: Optional[str] = None
    progress_percent: Optional[float] = None
    last_read: str

class ReadingProgressRequest(BaseModel):
    cfi_location: Optional[str] = None
    progress_percent: Optional[float] = None

class StartScanRequest(BaseModel):
    folder_path: Optional[str] = None
