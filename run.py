
import subprocess
import sys
import os

def main():
    processes = []
    # Запуск FastAPI
    api_cmd = [sys.executable, '-m', 'uvicorn', 'api.app:app', '--reload']
    processes.append(subprocess.Popen(api_cmd))
    # Запуск бота
    bot_cmd = [sys.executable, os.path.join('bot', 'run.py')]
    processes.append(subprocess.Popen(bot_cmd))
    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()

if __name__ == "__main__":
    main()
