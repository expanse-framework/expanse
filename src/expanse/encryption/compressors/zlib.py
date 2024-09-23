import zlib

from expanse.encryption.compressors.compressor import Compressor


class ZlibCompressor(Compressor):
    def compress(self, data: bytes) -> bytes:
        return zlib.compress(data)

    def decompress(self, data: bytes) -> bytes:
        return zlib.decompress(data)
