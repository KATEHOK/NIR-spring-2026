import os
import subprocess
import time
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    server_image_tag = os.getenv("SERVER_IMAGE_TAG", "unknown")
    locust_dir = "tests/locust"
    results_dir = f"{locust_dir}/results/{server_image_tag}"
    csv_dir = f"{results_dir}/csv"
    html_dir = f"{results_dir}/html"
    sleep_s = 60
    users_start = 640
    users_stop = 800 + 1
    users_step = 40
    host = "http://localhost:8000"
    spawn_rate = "100"
    run_time = "10m"
    os.makedirs(csv_dir, exist_ok=True)
    os.makedirs(html_dir, exist_ok=True)
    for users in range(users_start, users_stop, users_step):
        users = str(users)
        filename = f"{users}_{spawn_rate}_{run_time}"
        # Подменяем аргументы командной строки
        cmd = [
            "locust",
            "-f", f"{locust_dir}/locustfile.py",
            "--host", host,
            "--headless",
            "--users", users,
            "--spawn-rate", spawn_rate,
            "--run-time", run_time,
            "--csv", f"{csv_dir}/{filename}",
            "--html", f"{html_dir}/{filename}.html",
            "--exit-code-on-error", "0",
        ]
        subprocess.run(["python", f"{locust_dir}/cleanup_db.py"])
        subprocess.run(cmd)
        time.sleep(sleep_s)