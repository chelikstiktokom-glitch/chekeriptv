import requests
import os
from concurrent.futures import ThreadPoolExecutor

# Настройки консольных цветов (ANSI)
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

TIMEOUT = 5  # Время ожидания ответа
THREADS = 20 # Количество потоков

def get_channel_name(info_line):
    """Извлекает название канала из строки #EXTINF."""
    parts = info_line.split(',')
    if len(parts) > 1:
        return parts[-1].strip()
    return "Unknown Channel"

def check_channel(url, info):
    """Проверяет доступность URL и выводит результат в консоль."""
    name = get_channel_name(info)
    try:
        response = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        if response.status_code == 200:
            print(f"{GREEN}[OK] {name}{RESET}")
            return f"{info}\n{url}\n"
        else:
            print(f"{RED}[DEAD] {name} (Status: {response.status_code}){RESET}")
    except Exception:
        print(f"{RED}[ERROR] {name} (Timeout/Error){RESET}")
    
    return None

def main():
    if os.name == 'nt':
        os.system('color')

    print("1. Выбрать локальный файл (.m3u/.m3u8)")
    print("2. Проверить по прямой ссылке (URL)")
    
    mode = input("\nВыбери вариант: ")

    lines = []
    original_name = ""

    if mode == "1":
        files = [f for f in os.listdir('.') if f.lower().endswith(('.m3u', '.m3u8'))]
        if not files:
            print("Файлы не найдены.")
            return

        print("\nСписок плейлистов:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file}")

        try:
            choice = int(input("\nВыбери номер: ")) - 1
            if not (0 <= choice < len(files)):
                print("Ошибка: Неверный номер.")
                return
            input_file = files[choice]
            original_name = os.path.splitext(input_file)[0]
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except ValueError:
            print("Ошибка: Введите число.")
            return

    elif mode == "2":
        url_input = input("Введите URL плейлиста: ").strip()
        try:
            print("Загрузка плейлиста...")
            response = requests.get(url_input, timeout=10)
            response.raise_for_status()
            lines = response.text.splitlines()
            original_name = "url_playlist"
            input_file = "downloaded.m3u"
        except Exception as e:
            print(f"Ошибка при загрузке: {e}")
            return
    else:
        print("Неверный режим.")
        return

    # Подготовка папки
    output_dir = os.path.join("output", original_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Парсинг
    tasks = []
    current_info = None
    for line in lines:
        line = line.strip()
        if line.startswith('#EXTINF'):
            current_info = line
        elif line.startswith('http') and current_info:
            tasks.append((line, current_info))
            current_info = None

    if not tasks:
        print("В плейлисте не найдено ссылок на каналы.")
        return

    print(f"\nНачало проверки. Каналов обнаружено: {len(tasks)}\n")

    working_results = []
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = [executor.submit(check_channel, url, info) for url, info in tasks]
        for future in futures:
            result = future.result()
            if result:
                working_results.append(result)

    # Сохранение
    output_path = os.path.join(output_dir, f"checked_{original_name}.m3u")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.writelines(working_results)

    print("\n-----------------------------------")
    print("Проверка завершена.")
    print(f"Рабочих каналов: {len(working_results)} из {len(tasks)}")
    print(f"Результат сохранен в: {output_path}")

if __name__ == "__main__":
    main()