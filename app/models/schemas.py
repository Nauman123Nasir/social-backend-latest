from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class VideoFormat(BaseModel):
    format_id: str
    ext: str
    resolution: str
    filesize: Optional[int] = None
    url: str
    needs_merging: bool = False

class VideoInfoRequest(BaseModel):
    url: HttpUrl

class VideoInfoResponse(BaseModel):
    title: str
    thumbnail: Optional[str] = None
    duration: Optional[float] = None
    formats: List[VideoFormat]
    platform: str
