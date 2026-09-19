"""Fetch pinned, local-only GBA font and mGBA test/player runtime dependencies."""
import hashlib
import io
import tarfile
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FONT_URL='https://unifoundry.com/pub/unifont/unifont-16.0.04/font-builds/unifont-16.0.04.hex.gz'
FONT_SHA='f9c8c7802453f47be02677176aeac2342ee96d354fad7a26cedcce48e68e1d9f'
EMU_URL='https://registry.npmjs.org/@wasm-gaming/mgba-wasm/-/mgba-wasm-0.1.1.tgz'
EMU_SHA='8b4b68fcca464dfbb475da4cee14a65ebbe4df0e6db33f8122920b2b9a3ca26c'


def fetch(url,sha,path):
    data=path.read_bytes() if path.exists() else urllib.request.urlopen(url,timeout=60).read()
    if hashlib.sha256(data).hexdigest()!=sha:raise ValueError('Dependency checksum mismatch: '+url)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    return data


if __name__=='__main__':
    fetch(FONT_URL,FONT_SHA,ROOT/'.cache/toolchains/unifont-16.0.04.hex.gz')
    package=fetch(EMU_URL,EMU_SHA,ROOT/'.cache/toolchains/mgba-wasm-0.1.1.tgz')
    target=ROOT/'.cache/toolchains/mgba-wasm'
    with tarfile.open(fileobj=io.BytesIO(package),mode='r:gz') as archive:
        for member in archive.getmembers():
            if not member.isfile():continue
            path=target/Path(member.name).relative_to('package')
            if not path.resolve().is_relative_to(target.resolve()):raise ValueError('Unsafe archive member')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.extractfile(member).read())
    print('Pinned GNU Unifont and mGBA WebAssembly runtime verified; no system install.')
