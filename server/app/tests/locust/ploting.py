import pandas as pd
import matplotlib.pyplot as plt
import os
import re
from dotenv import load_dotenv

load_dotenv()

MIN_USERS = 40
MAX_USERS = 1200
IMAGE_TAG = os.getenv("SERVER_IMAGE_TAG", "unknown")
BASE_DIR = "tests/locust/results"
RESULTS_DIR = f"{BASE_DIR}/{IMAGE_TAG}"
IN_DIR = f"{RESULTS_DIR}/csv"
OUT_DIR = f"{RESULTS_DIR}/png/{MIN_USERS}_{MAX_USERS}"


def mkdir(dir_path: str):
    os.makedirs(dir_path, exist_ok=True)


def to_safe(unsafe: str) -> str:
    return unsafe.replace('/', '_').replace('\\', '_').strip('_')


def extract_users_from_filename(filename: str) -> int:
    """Извлекает число пользователей из имени файла (первое число до подчёркивания)."""
    match = re.match(r"(\d+)_", filename)
    if not match:
        raise ValueError(f"Filename '{filename}' does not start with a number followed by underscore.")
    return int(match.group(1))


def load_locust_data(filepath: str) -> pd.DataFrame:
    """Загружает CSV Locust, заменяет пустые строки в 'Type' на 'Aggregated' и возвращает DataFrame."""
    df = pd.read_csv(filepath, skipinitialspace=True)
    if 'Type' in df.columns and 'Name' in df.columns:
        df['Type'] = df['Type'].fillna('Aggregated')
        df.loc[df['Name'] == 'Aggregated', 'Type'] = 'Aggregated'
    return df


def safe_float_convert(series):
    """Конвертирует в float, заменяя нечисловые значения на NaN."""
    return pd.to_numeric(series, errors='coerce')


def prepare_endpoint_data(data_by_users: dict, endpoint: str, required_columns: list) -> dict:
    """
    data_by_users: {users: df}
    endpoint: название эндпоинта (или 'Aggregated')
    Возвращает словарь с метриками для построения графиков.
    """
    records = []
    for users, df in data_by_users.items():
        if endpoint == 'Aggregated':
            mask = df['Name'] == 'Aggregated'
        else:
            mask = (df['Name'] == endpoint) & (df['Type'] != 'Aggregated')
        row = df[mask]
        if len(row) == 0:
            continue
        row = row.iloc[0]

        record = {'users': users}
        for col in required_columns:
            val = row.get(col)
            if val is None or pd.isna(val):
                val = 0.0
            else:
                val = float(val)
            record[col] = val

        req_cnt = record.get('Request Count', 0)
        fail_cnt = record.get('Failure Count', 0)
        record['Failure %'] = (fail_cnt / req_cnt * 100) if req_cnt > 0 else 0.0

        records.append(record)

    records.sort(key=lambda x: x['users'])
    if not records:
        return {}

    result = {col: [rec[col] for rec in records] for col in records[0].keys()}
    result['users'] = result.pop('users')
    return result


def plot_requests_chart(endpoint_data: dict, endpoint_name: str, out_dir: str):
    """График: Request Count и Failure % (две оси)"""
    users = endpoint_data['users']
    req_cnt = endpoint_data['Request Count']
    fail_pct = endpoint_data['Failure %']

    fig, ax1 = plt.subplots(figsize=(16, 9), dpi=100)
    ax2 = ax1.twinx()

    ax1.plot(users, req_cnt, color='blue', marker='o', linewidth=2, label='Request Count')
    ax2.plot(users, fail_pct, color='red', marker='s', linewidth=2, label='Failure %')

    ax1.set_xlabel('Число одновременных пользователей', fontsize=12)
    ax1.set_ylabel('Количество запросов', color='blue', fontsize=12)
    ax2.set_ylabel('Процент ошибок (%)', color='red', fontsize=12)

    ax1.tick_params(axis='y', labelcolor='blue')
    ax2.tick_params(axis='y', labelcolor='red')

    plt.title(f'{endpoint_name} - Requests & Failure %', fontsize=14)
    plt.tight_layout()

    out_dir = f"{out_dir}/{to_safe(endpoint_name)}"
    mkdir(out_dir)
    filename = "requests.png"
    filepath = f"{out_dir}/{filename}"
    plt.savefig(filepath)
    plt.close()
    print(f"Saved: {filepath}")


def plot_time_min_max_chart(endpoint_data: dict, endpoint_name: str, out_dir: str):
    """График: Min и Max время ответа (две оси)"""
    users = endpoint_data['users']
    min_time = endpoint_data['Min Response Time']
    max_time = endpoint_data['Max Response Time']

    fig, ax1 = plt.subplots(figsize=(16, 9), dpi=100)
    ax2 = ax1.twinx()

    ax1.plot(users, min_time, color='green', marker='o', linewidth=2, label='Min Response Time')
    ax2.plot(users, max_time, color='red', marker='s', linewidth=2, label='Max Response Time')

    ax1.set_xlabel('Число одновременных пользователей', fontsize=12)
    ax1.set_ylabel('Минимальное время (мс)', color='green', fontsize=12)
    ax2.set_ylabel('Максимальное время (мс)', color='red', fontsize=12)

    ax1.tick_params(axis='y', labelcolor='green')
    ax2.tick_params(axis='y', labelcolor='red')

    plt.title(f'{endpoint_name} - Min / Max Response Time', fontsize=14)
    plt.tight_layout()

    out_dir = f"{out_dir}/{to_safe(endpoint_name)}"
    mkdir(out_dir)
    filename = "time_min-max.png"
    filepath = f"{out_dir}/{filename}"
    plt.savefig(filepath)
    plt.close()
    print(f"Saved: {filepath}")


def plot_time_med_avg_chart(endpoint_data: dict, endpoint_name: str, out_dir: str):
    """График: Median (50%) и Average время ответа (две оси)"""
    users = endpoint_data['users']
    median = endpoint_data.get('50%', endpoint_data.get('Median Response Time', [0] * len(users)))
    avg = endpoint_data['Average Response Time']

    fig, ax1 = plt.subplots(figsize=(16, 9), dpi=100)
    ax2 = ax1.twinx()

    ax1.plot(users, median, color='red', marker='o', linewidth=2, label='Median (50%)')
    ax2.plot(users, avg, color='purple', marker='s', linewidth=2, label='Average Response Time')

    ax1.set_xlabel('Число одновременных пользователей', fontsize=12)
    ax1.set_ylabel('Медианное время (мс)', color='red', fontsize=12)
    ax2.set_ylabel('Среднее время (мс)', color='purple', fontsize=12)

    ax1.tick_params(axis='y', labelcolor='red')
    ax2.tick_params(axis='y', labelcolor='purple')

    plt.title(f'{endpoint_name} - Median / Average Response Time', fontsize=14)
    plt.tight_layout()

    out_dir = f"{out_dir}/{to_safe(endpoint_name)}"
    mkdir(out_dir)
    filename = "time_med-avg.png"
    filepath = f"{out_dir}/{filename}"
    plt.savefig(filepath)
    plt.close()
    print(f"Saved: {filepath}")


def plot_rps_fps_chart(endpoint_data: dict, endpoint_name: str, out_dir: str):
    """График: Requests/s и Failures/s (две оси)"""
    users = endpoint_data['users']
    rps = endpoint_data['Requests/s']
    fps = endpoint_data['Failures/s']

    fig, ax1 = plt.subplots(figsize=(16, 9), dpi=100)
    ax2 = ax1.twinx()

    ax1.plot(users, rps, color='green', marker='o', linewidth=2, label='Requests/s')
    ax2.plot(users, fps, color='red', marker='s', linewidth=2, label='Failures/s')

    ax1.set_xlabel('Число одновременных пользователей', fontsize=12)
    ax1.set_ylabel('Запросов в секунду', color='green', fontsize=12)
    ax2.set_ylabel('Ошибок в секунду', color='red', fontsize=12)

    ax1.tick_params(axis='y', labelcolor='green')
    ax2.tick_params(axis='y', labelcolor='red')

    plt.title(f'{endpoint_name} - Requests/s & Failures/s', fontsize=14)
    plt.tight_layout()

    out_dir = f"{out_dir}/{to_safe(endpoint_name)}"
    mkdir(out_dir)
    filename = "rps-fps.png"
    filepath = f"{out_dir}/{filename}"
    plt.savefig(filepath)
    plt.close()
    print(f"Saved: {filepath}")


def main():
    if not os.path.isdir(IN_DIR):
        raise Exception(f"Input directory '{IN_DIR}' does not exist.")
    mkdir(OUT_DIR)
    
    # 1. Поиск файлов
    all_files = [f for f in os.listdir(IN_DIR) if f.endswith('_stats.csv')]
    if not all_files:
        raise Exception(f"No '_stats.csv' files found in '{IN_DIR}'.")

    # 2. Фильтрация по диапазону пользователей
    valid_files = []
    for f in all_files:
        try:
            users = extract_users_from_filename(f)
            if MIN_USERS <= users <= MAX_USERS:
                valid_files.append((users, f))
        except ValueError as e:
            print(f"Skipping file {f}: {e}")
            continue

    if not valid_files:
        raise Exception(f"No files with users in range [{MIN_USERS}, {MAX_USERS}] found.")

    valid_files.sort(key=lambda x: x[0])
    print(f"Found {len(valid_files)} files within user range: {[u for u, _ in valid_files]}")

    # 3. Загрузка всех данных в словарь {users: df}
    data_by_users = {}
    for users, fname in valid_files:
        filepath = os.path.join(IN_DIR, fname)
        df = load_locust_data(filepath)
        data_by_users[users] = df
        print(f"Loaded {fname} (users={users})")

    # 4. Определяем все эндпоинты (включая Aggregated)
    all_endpoints = set()
    for df in data_by_users.values():
        # Обычные эндпоинты (Type не равен 'Aggregated', Name не 'Aggregated')
        endpoints = df[df['Type'] != 'Aggregated']['Name'].unique()
        all_endpoints.update(endpoints)
    # Добавляем агрегированную строку, если она есть хотя бы в одном файле
    if any('Aggregated' in df['Name'].values for df in data_by_users.values()):
        all_endpoints.add('Aggregated')

    print(f"Endpoints to process: {list(all_endpoints)}")

    # Список необходимых колонок для извлечения
    required_columns = [
        'Request Count', 'Failure Count', 'Min Response Time', 'Median Response Time',
        'Average Response Time', 'Max Response Time', 'Requests/s', 'Failures/s'
    ]

    # 5. Для каждого эндпоинта собираем данные и строим графики
    for endpoint in all_endpoints:
        print(f"\nProcessing endpoint: {endpoint}")
        data = prepare_endpoint_data(data_by_users, endpoint, required_columns)
        if not data:
            print(f"  No data for {endpoint}, skipping.")
            continue
        # Проверяем, что есть хотя бы две точки (для осмысленного графика)
        if len(data['users']) < 2:
            print(f"  Only {len(data['users'])} point(s) for {endpoint}, skipping plots (need at least 2).")
            continue

        # Строим 4 графика
        plot_requests_chart(data, endpoint, OUT_DIR)
        plot_time_min_max_chart(data, endpoint, OUT_DIR)
        plot_time_med_avg_chart(data, endpoint, OUT_DIR)
        plot_rps_fps_chart(data, endpoint, OUT_DIR)

    print("\nAll plots generated successfully.")


if __name__ == "__main__":
    main()