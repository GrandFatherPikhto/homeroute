#!/usr/bin/env python3
import json
import subprocess
import sys
import os
from datetime import datetime

ROUTE_BACKUP_FILE = "/var/lib/openvpn/routes_backup.json"

def get_current_routes():
    """Получает текущую таблицу маршрутизации"""
    result = subprocess.run(['ip', 'route', 'show'], capture_output=True, text=True)
    return result.stdout.splitlines()

def save_routes(routes):
    """Сохраняет маршруты в файл"""
    os.makedirs(os.path.dirname(ROUTE_BACKUP_FILE), exist_ok=True)
    with open(ROUTE_BACKUP_FILE, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'routes': routes
        }, f)

def load_routes():
    """Загружает сохранённые маршруты"""
    with open(ROUTE_BACKUP_FILE) as f:
        return json.load(f)['routes']

def setup_vpn_routes():
    """Настраивает маршруты для VPN"""
    # Пример: только трафик к определенным хостам через VPN
    vpn_routes = [
        ('youtube.com', '255.255.255.255'),
        ('api.st.com', '255.255.255.255'),
        ('10.95.2.0', '255.255.255.192', '10.95.2.1')  # Локальная сеть
    ]
    
    for route in vpn_routes:
        if len(route) == 2:
            subprocess.run(['ip', 'route', 'add', route[0], 'via', '10.8.0.1', 'dev', 'tun0'])
        else:
            subprocess.run(['ip', 'route', 'add', route[0], 'via', route[2], 'dev', 'enp2s0'])

def restore_original_routes():
    """Восстанавливает оригинальные маршруты"""
    try:
        original_routes = load_routes()
        # Удаляем все текущие маршруты
        subprocess.run(['ip', 'route', 'flush', 'all'])
        # Восстанавливаем оригинальные
        for route in original_routes:
            subprocess.run(['ip', 'route', 'add'] + route.split())
    except FileNotFoundError:
        print("Backup file not found, skipping restore")

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <up|down>")
        sys.exit(1)

    if sys.argv[1] == 'up':
        # Сохраняем текущие маршруты
        save_routes(get_current_routes())
        # Настраиваем VPN-маршруты
        setup_vpn_routes()
        print("VPN routes configured")
    elif sys.argv[1] == 'down':
        restore_original_routes()
        print("Original routes restored")
    else:
        print("Invalid argument. Use 'up' or 'down'")

if __name__ == "__main__":
    main()
    