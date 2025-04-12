#!/usr/bin/env python3
import os
import sys
import shutil

# Цвета для вывода
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.GREEN}{text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}{text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}{text}{Colors.ENDC}")

def main():
    print_header("\n=== Настройка бота Kisel Bot ===\n")
    
    # Проверка наличия файла config.py.example
    if not os.path.exists("config.py.example"):
        print_error("Ошибка: Файл config.py.example не найден!")
        sys.exit(1)
    
    # Проверка существования config.py
    if os.path.exists("config.py"):
        print_warning("Файл config.py уже существует.")
        overwrite = input("Перезаписать? (y/n): ").lower()
        if overwrite != 'y':
            print_warning("Настройка отменена.")
            sys.exit(0)
    
    # Копирование шаблона
    shutil.copy("config.py.example", "config.py")
    print_success("Файл config.py создан из шаблона.")
    
    # Ввод токена
    token = input("Введите токен бота Discord: ")
    if not token:
        print_error("Токен не может быть пустым!")
        return
    
    # Ввод ID серверов
    guild_ids_input = input("Введите ID серверов через запятую (например: 123456789,987654321) или оставьте пустым: ")
    guild_ids = []
    
    if guild_ids_input:
        try:
            guild_ids = [int(gid.strip()) for gid in guild_ids_input.split(",") if gid.strip()]
        except ValueError:
            print_error("Ошибка: ID серверов должны быть числами!")
            return
    
    # Чтение файла конфигурации
    with open("config.py", "r", encoding="utf-8") as f:
        config_content = f.read()
    
    # Замена значений
    config_content = config_content.replace("ВСТАВЬТЕ_ВАШ_ТОКЕН_СЮДА", token)
    
    # Настройка ID серверов если они есть
    if guild_ids:
        if "# GUILD_IDS" in config_content:
            config_content = config_content.replace(
                "# GUILD_IDS = [123456789, 987654321]", 
                f"GUILD_IDS = {guild_ids}"
            )
    
    # Сохранение конфигурации
    with open("config.py", "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print_success("\nБот успешно настроен!")
    print_success("Теперь вы можете запустить бота командой: python bot.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\nНастройка прервана пользователем.")
        sys.exit(0) 