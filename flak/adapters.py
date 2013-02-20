import os

from mutagen.flac import CueSheet
from mutagen.flac import Padding
from mutagen.flac import Picture
from mutagen.flac import SeekTable
from mutagen.flac import StreamInfo
from mutagen.flac import VCFLACDict

def datetime(obj, request):
    return obj.isoformat()

def attrs(obj, request):
    return obj.__dict__

def seektable(obj, request):
    my_attrs = dict(
        seekpoints=[
            dict(first_sample=sp.first_sample,
                 byte_offset=sp.byte_offset,
                 num_samples=sp.num_samples)
            for sp in obj.seekpoints
        ]
    )
    return my_attrs

def cuesheet(obj, request):
    my_attrs = obj.__dict__
    tracks = []
    for i in range(obj.tracks):
        track = obj.tracks[i]
        track_attrs = track.__dict__
        indexes = []
        for j in range(track.indexes):
            track_index = track.indexes[j]
            indexes.append(dict(index_number=track_index.index_number,
                                index_offset=track_index.index_offset))
        track_attrs['indexes'] = indexes
    my_attrs['tracks'] = tracks
    return my_attrs

def picture(obj, request):
    return obj.data.encode('base64')

def flac(obj, request):
    from datetime import datetime
    statinfo = os.stat(obj.filename)
    blocks = {
        'path': obj.filename,
        'size': statinfo.st_size,
        'mtime': datetime.fromtimestamp(statinfo.st_mtime),
        'signature': '%x' % obj.info.md5_signature,
    }
    for block in obj.metadata_blocks:
        if isinstance(block, StreamInfo):
            blocks['stream_info'] = block
        elif isinstance(block, SeekTable):
            blocks['seek_table'] = block
        elif isinstance(block, VCFLACDict):
            blocks['tags'] = dict(block)
        elif isinstance(block, CueSheet):
            blocks['cue_sheet'] = block
        elif isinstance(block, Picture):
            blocks.setdefault('picture', []).append(block)
        elif isinstance(block, Padding):
            blocks.setdefault('padding', []).append(block)
    return blocks
