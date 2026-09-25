import hashlib


def stable_tick_id(source: str, source_record_id: str) -> str:
    return hashlib.sha256(f'{source}|{source_record_id}'.encode()).hexdigest()[:24]
