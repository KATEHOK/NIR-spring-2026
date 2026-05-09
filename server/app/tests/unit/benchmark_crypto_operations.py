import asyncio
import time
import os
import csv
from typing import Callable
from datetime import timedelta
from src.crypt import Password, SymmetricEncryption, JWT, Random
from src.utils import datetime_utcnow


def log_result(experiment_id: str, async_mode: bool, func_name: str, calls_count: int, elapsed_ms: float, csv_file: str):
    """Добавляет строку в CSV-файл с результатами."""
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["experiment_id", "async_mode", "func_name", "calls_count", "elapsed_ms"])
        writer.writerow([experiment_id, async_mode, func_name, calls_count, f"{elapsed_ms:.3f}"])
    print(experiment_id, async_mode, func_name, calls_count, f"{elapsed_ms:.3f}", sep=" | ")


def gen_password_and_hash(length: int = 16) -> tuple[str, bytes]:
    password = Random.urlsafe(length)
    return password, Password.hash(password)

async def gen_passwords_and_hashes(count: int = 10, length: int = 16) -> tuple[tuple[str, ...], tuple[bytes, ...]]:
    """Генерирует рандомные urlsafe пароли и вычисляет их хэши"""
    tasks = [asyncio.to_thread(gen_password_and_hash, length) for _ in range(count)]
    results = await asyncio.gather(*tasks)
    pws, hs = zip(*results)
    return pws, hs


def gen_payload_and_jwt() -> tuple[dict, str]:
    now_aware = datetime_utcnow(False)
    payload = {
        "sub": Random.urlsafe(8),
        "refresh_id": Random.urlsafe(8),
        "iat": int(now_aware.timestamp()),
        "exp": int((now_aware + timedelta(minutes=JWT.access_token_expire_minutes)).timestamp()),
        "type": "access"
    }
    return payload, JWT.encode(payload)

async def gen_payloads_and_jwts(count: int = 10) -> tuple[tuple[dict, ...], tuple[str, ...]]:
    """Генерирует полезную нагрузку и jwt"""
    tasks = [asyncio.to_thread(gen_payload_and_jwt) for _ in range(count)]
    results = await asyncio.gather(*tasks)
    payloads, jwts = zip(*results)
    return payloads, jwts


def gen_plain_and_encrypted_bytes(
        length: int = 32,
        key_length: int = None,
) -> tuple[bytes, bytes, bytes | None]:
    key = None if key_length is None else Random.bytes(key_length)
    plain = Random.bytes(length)
    return plain, SymmetricEncryption.encrypt(plain, key), key

async def gen_pairs_plain_and_encrypted_bytes(
        count: int = 10,
        length: int = 32,
        key_length: int = None,
) -> tuple[tuple[bytes, ...], tuple[bytes, ...], tuple[bytes | None, ...]]:
    """Генерирует данные, шифртекст и (опционально) личный ключ"""
    tasks = [asyncio.to_thread(gen_plain_and_encrypted_bytes, length, key_length) for _ in range(count)]
    results = await asyncio.gather(*tasks)
    plain, encrypted, keys = zip(*results)
    return plain, encrypted, keys


async def benchmark_sync_vs_threaded(
        async_mode: bool,
        funcs: tuple[Callable, ...],
        funcs_args_collections: tuple[tuple[tuple, ...], ...],
        experiment_id: str,
        result_csv_filename: str,
):
    for func, args_collections in zip(funcs, funcs_args_collections):
        if async_mode:
            start = time.perf_counter()
            tasks = [asyncio.to_thread(func, *args_collection) for args_collection in args_collections]
            await asyncio.gather(*tasks)
        else:
            start = time.perf_counter()
            for args_collection in args_collections:
                func(*args_collection)
        elapsed_ms = (time.perf_counter() - start) * 1000
        log_result(experiment_id, async_mode, func.__name__, len(args_collections), elapsed_ms, result_csv_filename)


async def main(
    experiment_id: str = Random.urlsafe(8),
    call_count: int = 100,
    csv_filename: str = "tests/unit/results_benchmark_sync_vs_threaded.csv",

    password_length: int = 16,
    plain_length: int = 1024,
    key_length: int = None,
):
    # Data generation
    (passwords, hashes), (payloads, jwts), (plain, encrypted, keys) = await asyncio.gather(
        gen_passwords_and_hashes(call_count, password_length),
        gen_payloads_and_jwts(call_count),
        gen_pairs_plain_and_encrypted_bytes(call_count, plain_length, key_length),
    )

    # Experiment runtime
    for funcs, funcs_args_collections in (
        (
            (Password.hash, Password.verify),
            (tuple(zip(passwords)), tuple(zip(passwords, hashes)))
        ),
        (
            (JWT.encode, JWT.decode),
            (tuple(zip(payloads)), tuple(zip(jwts)))
        ),
        (
            (SymmetricEncryption.encrypt, SymmetricEncryption.decrypt),
            (tuple(zip(plain, keys)), tuple(zip(encrypted, keys)))
        ),
    ):
        for async_mode in (False, True):
            await benchmark_sync_vs_threaded(
                async_mode=async_mode,
                funcs=funcs,
                funcs_args_collections=funcs_args_collections,
                experiment_id=experiment_id,
                result_csv_filename=csv_filename
            )


if __name__ == "__main__":
    asyncio.run(main())
