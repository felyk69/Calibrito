from pydantic import BaseModel


class BookModel(BaseModel):
    id: int
    title: str
    author: str
    file_path: str
    file_type: str
    cover_path: str | None = None
    added_date: str | None = None
    series: str | None = None
    volume: float | None = None
    synopsis: str | None = None
    publisher: str | None = None
    publish_year: int | None = None


class SendBookRequest(BaseModel):
    id: int
    kindle_path: str = ""


class UpdateBookRequest(BaseModel):
    title: str
    author: str
    series: str | None = None
    volume: float | None = None
    synopsis: str | None = None
    publisher: str | None = None
    publish_year: int | None = None


class DeleteBookRequest(BaseModel):
    ids: list[int]
    permanent: bool = False


class DownloadCoverRequest(BaseModel):
    url: str


class SettingsRequest(BaseModel):
    books_folder: str
    scanner_threads: int = 2
    rescan: bool = True


class ProfileModel(BaseModel):
    id: int
    name: str
    avatar: str | None = None


class ProfileCreateRequest(BaseModel):
    name: str
    avatar: str | None = None


class ReadingProgressModel(BaseModel):
    id: int
    profile_id: int
    book_id: int
    cfi_location: str | None = None
    progress_percent: float | None = None
    last_read: str


class ReadingProgressRequest(BaseModel):
    cfi_location: str | None = None
    progress_percent: float | None = None


class StartScanRequest(BaseModel):
    folder_path: str | None = None
