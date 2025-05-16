#!/usr/bin/env python3
from pyroute2 import IPRoute
import json
import sys
import os

TUN_IFACE = "tun0"
CONFIG_FILE = "./tun_routes.json"  # Файл конфигурации маршрутов
BACKUP_FILE = "./route_backup.json"  # Файл для резервного копирования текущих маршрутов

DEFAULT_CONFIG = {
    "tun_ip": "10.109.154.78/21",
    "routes": [
        {"dst": "192.168.100.0/24", "gateway": "10.8.0.1", "metric": 100},
        {"dst": "172.16.0.0/16", "gateway": "10.8.0.1", "metric": 200}
    ]
}

def load_config():
    """Загружает конфигурацию из файла или создает default конфиг."""
    if not os.path.exists(CONFIG_FILE):
        print(f"[!] Файл конфигурации {CONFIG_FILE} не найден, создаю default")
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_routes():
    """Сохраняет текущие маршруты в файл."""
    ip = IPRoute()
    routes = []
    for route in ip.get_routes():
        routes.append({
            "dst": route.get_attr("RTA_DST", ""),
            "gateway": route.get_attr("RTA_GATEWAY", ""),
            "oif": route.get_attr("RTA_OIF", ""),
            "table": route.get_attr("RTA_TABLE", 0),
            "priority": route.get_attr("RTA_PRIORITY", 0),
            "scope": route.get_attr("RTA_SCOPE", 0),
            "proto": route.get_attr("RTA_PROTO", 0),
        })
    with open(BACKUP_FILE, "w") as f:
        json.dump(routes, f, indent=4)
    ip.close()
    print(f"[+] Сохранено {len(routes)} маршрутов в {BACKUP_FILE}")

def restore_routes():
    """Восстанавливает маршруты из файла."""
    if not os.path.exists(BACKUP_FILE):
        print("[-] Файл с резервной копией маршрутов не найден!")
        return

    config = load_config()
    ip = IPRoute()
    
    # Удаляем только маршруты из конфигурации
    for route in config["routes"]:
        try:
            route_kwargs = {"dst": route["dst"]}
            if "gateway" in route:
                route_kwargs["gateway"] = route["gateway"]
            if "metric" in route:
                route_kwargs["priority"] = route["metric"]
            ip.route("del", **route_kwargs)
            print(f"[+] Удален маршрут: {route['dst']}")
        except Exception as e:
            print(f"[-] Ошибка удаления маршрута {route}: {e}")

    # Восстанавливаем оригинальные маршруты
    with open(BACKUP_FILE, "r") as f:
        routes = json.load(f)
    
    for route in routes:
        try:
            if route["dst"] or route["gateway"]:  # Пропускаем пустые маршруты
                ip.route("add", **{
                    "dst": route["dst"],
                    "gateway": route["gateway"],
                    "oif": route["oif"],
                    "table": route["table"],
                    "priority": route["priority"],
                    "scope": route["scope"],
                    "proto": route["proto"],
                })
        except Exception as e:
            print(f"[-] Ошибка восстановления маршрута {route}: {e}")
    
    os.remove(BACKUP_FILE)
    ip.close()
    print("[+] Таблица маршрутизации восстановлена")

def tun_up():
    """Добавляет маршруты через tun0 интерфейс согласно конфигурации."""
    save_routes()  # Сначала сохраняем текущие маршруты
    
    config = load_config()
    ip = IPRoute()
    
    # Проверяем существование интерфейса tun0
    idx = ip.link_lookup(ifname=TUN_IFACE)
    if not idx:
        print(f"[-] Интерфейс {TUN_IFACE} не найден!")
        ip.close()
        return

    print(f"[+] Добавляю маршруты через {TUN_IFACE} из конфигурации...")
    
    for route in config["routes"]:
        try:
            # Если gateway не указан, используем IP tun-интерфейса
            gateway = route.get("gateway", config["tun_ip"].split('/')[0])
            
            route_kwargs = {
                "dst": route["dst"],
                "gateway": gateway,
            }
            
            if "metric" in route:
                route_kwargs["priority"] = route["metric"]
            
            ip.route("add", **route_kwargs)
            print(f"[+] Добавлен маршрут: {route['dst']} через {gateway}" + 
                 (f" с метрикой {route['metric']}" if "metric" in route else ""))
        except Exception as e:
            print(f"[-] Ошибка добавления маршрута {route}: {e}")
    
    ip.close()

def tun_down():
    """Удаляет маршруты и восстанавливает оригинальные."""
    restore_routes()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: sudo ./tun_route_manager.py <up|down>")
        print(f"Конфигурация: {CONFIG_FILE}")
        sys.exit(1)
    
    if sys.argv[1] == "up":
        tun_up()
    elif sys.argv[1] == "down":
        tun_down()
    else:
        print("Ошибка: допустимые аргументы — 'up' или 'down'")