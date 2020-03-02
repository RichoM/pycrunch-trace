import io
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import List

import jsonpickle

from pycrunch_tracer.file_system.human_readable_size import HumanReadableByteSize


class TraceSessionMetadata:
    # time in UTC
    start_time: datetime
    end_time: datetime
    # size in bytes
    file_size_in_bytes: int
    file_size_on_disk: str
    files_in_session: List[str]

    events_in_session: int

    working_directory: str

    name: str


class LazyLoadedSession:
    metadata: TraceSessionMetadata
    buffer_file: Path
    metadata_file: Path
    raw_metadata: dict

    def __init__(self, buffer_file: Path, metadata_file: Path):
        self.buffer_file = buffer_file
        self.metadata_file = metadata_file
        self.raw_metadata = None

    def load_buffer(self):
        with io.FileIO(self.buffer_file, mode='r') as file:
            buffer = file.readall()
            # try:
                # result = json.loads(buffer)
            # except:
            result = pickle.loads(buffer)

            return result

    def load_metadata(self):
        with io.FileIO(self.metadata_file, 'r') as file:
            file_bytes = file.readall()
            json_representation = file_bytes.decode('utf-8')
            json_dict = json.loads(json_representation)
            self.raw_metadata = json_dict
            meta = TraceSessionMetadata()
            meta.files_in_session = json_dict.get('files_in_session')
            meta.excluded_files = json_dict.get('events_in_session')
            meta.events_in_session = json_dict.get('events_in_session')
            meta.file_size_in_bytes = json_dict.get('file_size_in_bytes')
            meta.file_size_on_disk = json_dict.get('file_size_on_disk')
            meta.name = json_dict.get('name')
            self.metadata = meta


class PersistedSession:
    def __init__(self, session_directory: Path):
        self.session_directory = session_directory

    metadata_filename = 'pycrunch-trace.meta.json'
    recording_filename = 'session.pycrunch-trace'

    pass

    def save_with_metadata(self, event_buffer, files_in_session, excluded_files):
        file_to_save = self.session_directory.joinpath(self.recording_filename)
        meta = TraceSessionMetadata()
        bytes_written = -42
        with io.FileIO(file_to_save, mode='w') as file:
            result = self.serialize_to_bytes(event_buffer)
            bytes_written = file.write(result)

        meta.files_in_session = list(files_in_session)
        meta.excluded_files = list(excluded_files)
        meta.file_size_in_bytes = bytes_written
        meta.file_size_on_disk = str(HumanReadableByteSize(bytes_written))
        meta.events_in_session = len(event_buffer)
        meta.name = str(self.session_directory)

        self.save_metadata(self.session_directory, meta)

    def serialize_to_bytes(self, event_buffer):
        return pickle.dumps(event_buffer)

    def save_metadata(self, session_directory: Path, meta: TraceSessionMetadata):
        metadata_file_path = session_directory.joinpath(self.metadata_filename)

        with io.FileIO(metadata_file_path, mode='w') as file:
            result = self.serialize_to_json(meta)
            bytes_written = file.write(result.encode('utf-8'))

    def serialize_to_json(self, meta) -> str:
        return jsonpickle.dumps(meta, unpicklable=False)

    @classmethod
    def load_from_directory(cls, load_from_directory: Path) -> LazyLoadedSession:
        joinpath = load_from_directory.joinpath(PersistedSession.recording_filename)
        print(joinpath)
        return LazyLoadedSession(joinpath, load_from_directory.joinpath(PersistedSession.metadata_filename))
