from core.utils.chunks import batched


STRING_CHUNK_SIZE = 80


def prepare_static_string_chunks(
    strings: list[str],
    chunk_size: int = STRING_CHUNK_SIZE,
) -> list[list[str]]:
    return batched(strings, chunk_size)
