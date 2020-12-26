from typing import Optional
from fastapi import FastAPI, Body
from pydantic import BaseModel

import threading
import pytube
import datetime
import toml
import regex
import urllib.request
import os

app = FastAPI()

class DownloadIn(BaseModel):
    url: str = 'URL'
    filter: dict = { 'mime_type' : 'video/mp4' }
    order_by: str = 'resolution'
    order: str = 'descending'
    index: int = 0

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

        config = toml.load('config.toml')

        dl_args = { 'output_path': config['output_path'], 'filename': regex.sub(r'\.[0-9a-z]+$', '', stream.default_filename ) }

        if config['podcast']:
            for podcast in config['podcast']:
                if regex.search(podcast['match'], stream.title):
                    dl_args['output_path'] += ( 'podcasts/' + podcast['name'] )

                    episode_number = regex.search(podcast['episode_number'], stream.title).group(0).strip()
                    episode_name = regex.search(podcast['episode_name'], stream.title).group(0).strip()

                    dl_args['filename'] = podcast['name'] + ' - ' + 'S00E' + episode_number + ' - ' + pytube.helpers.safe_filename(episode_name)
                    
                    lines = [
                        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>',
                        "<episodedetails>",
                        "\t<title>" + episode_name + "</title>",
                        "\t<episode>" + episode_number + "</episode>",
                        "\t<season>1</season>",
                        "</episodedetails>"
                    ]

                    os.makedirs(dl_args['output_path'], exist_ok=True)

                    with open(dl_args['output_path'] + '/' + dl_args['filename'] + '.nfo', 'w') as file:
                        for line in lines:
                            file.write(line + "\n")


            
        os.makedirs(dl_args['output_path'], exist_ok=True)
        urllib.request.urlretrieve(yt_obj.thumbnail_url, dl_args['output_path'] + '/' + dl_args['filename'] + '.png')
        dl_thread = threading.Thread( target = stream.download, kwargs = dl_args )
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