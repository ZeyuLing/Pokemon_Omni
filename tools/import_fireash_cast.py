"""Import hash-locked PNG entries from the developer's public ZIP, without executing it."""
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArchiveRanges(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.position = url, size, 0

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset + (0 if whence == 0 else self.position if whence == 1 else self.size)
        if not 0 <= self.position <= self.size:
            raise ValueError('Invalid ZIP seek')
        return self.position

    def read(self, count=-1):
        count = min(self.size-self.position, count if count >= 0 else self.size)
        if count == 0:
            return b''
        if count > 8 * 1024 * 1024:
            raise ValueError('Unexpectedly large ZIP range')
        req = urllib.request.Request(self.url, headers={
            'Range': f'bytes={self.position}-{self.position+count-1}',
            'User-Agent': 'PokemonOmni-local-asset-import/1.0'})
        with urllib.request.urlopen(req, timeout=40) as response:
            expected = f'bytes {self.position}-{self.position+count-1}/{self.size}'
            if response.status != 206 or response.headers.get('Content-Range') != expected:
                raise ValueError('Source archive size/range changed')
            data = response.read(count + 1)
        if len(data) != count:
            raise ValueError('Incomplete archive range')
        self.position += count
        return data


def main():
    manifest = json.loads((ROOT / 'assets/source/fireash-cast.json').read_text('utf-8'))
    archive = None
    for item in manifest['sprites']:
        path = ROOT / item['source_path']
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']:
            continue
        if archive is None:
            archive = zipfile.ZipFile(ArchiveRanges(manifest['archive_url'], manifest['archive_bytes']))
        info = archive.getinfo(item['archive_entry'])
        if info.file_size > 1024 * 1024:
            raise ValueError('Unexpected sprite size')
        data = archive.read(info)
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Source PNG changed: ' + item['actor'])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if archive:
        archive.close()
    print('Verified local Fire Ash Gary and Paul source PNGs')


if __name__ == '__main__':
    main()
