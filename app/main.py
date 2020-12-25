from typing import Optional
from fastapi import FastAPI, Body
from pydantic import BaseModel

import threading
import pytube
import datetime

app = FastAPI()

class DownloadIn(BaseModel):
    url: str = 'URL'
    filter: dict = { 'mime_type' : 'video/mp4' }
    order_by: str = 'resolution'
    order: str = 'descending'
    index: int = 0
    subdir: str = ''

class DownloadOut(DownloadIn):
    _current_downloads = []
    
    started: datetime.datetime = datetime.datetime.now()
    percent: float = 0

    def start(self):
        self._current_downloads.append(self)
        yt_obj = pytube.YouTube(self.url)
        
        yt_obj.register_on_progress_callback(self.progress_callback)
        yt_obj.register_on_complete_callback(self.complete_callback)
        
        query = yt_obj.streams.filter(**self.filter).order_by(self.order_by)

        if self.order == 'descending':
            stream = query.desc()[self.index]
        else:
            stream = query.asc()[self.index]

        dl_thread = threading.Thread( target = stream.download, args=['./downloads/' + self.subdir] )
        dl_thread.start()

    def progress_callback(self, stream: pytube.Stream, chunk, bytes_remaning):
        percent = 100 * (stream.filesize - bytes_remaning) / stream.filesize
        self.percent = percent
    
    def complete_callback(self, stream: pytube.Stream, path: str):
        self.percent = 100
        self._current_downloads.remove(self)

@app.post("/api/downloads/start")
def create_item(download_in: DownloadIn):
    dl_out = DownloadOut(**download_in.dict())
    dl_out.start()

    return dl_out

@app.get("/api/downloads/current")
def read_item():
    return DownloadOut._current_downloads