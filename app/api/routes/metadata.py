from fastapi import APIRouter

from app.models.schemas import DownloadCoverRequest
from app.services.metadata_service import download_cover, search_metadata

router = APIRouter(prefix="/api/v1/metadata", tags=["Metadata"])


@router.get("/search")
def search_metadata_route(q: str):
    return search_metadata(q)


@router.post("/books/{book_id}/download-cover")
def auto_download_cover(book_id: int, req: DownloadCoverRequest):
    cover_path_db = download_cover(book_id, req.url)
    return {"status": "success", "cover_path": cover_path_db}
