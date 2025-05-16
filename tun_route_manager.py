#!/usr/bin/env python3
from pyroute2 import IPRoute
import json
import sys
import os

TUN_IFACE = "tun0"
CONFIG_FILE = "./tun_routes.json"
BACKUP_FILE = "./route_backup.json"

def load_config():
    """Загружает конфигурацию из файла или создает default конфиг."""
    if not os.path.exists(CONFIG_FILE):
        return None
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


def get_tun_ip():
    """Получает IP-адрес tun0 интерфейса"""
    ip = IPRoute()
    try:
        # Ищем интерфейс tun0
        idx = ip.link_lookup(ifname=TUN_IFACE)
        if not idx:
            print(f"[-] Интерфейс {TUN_IFACE} не найден!")
            return None
        
        # Получаем все адреса интерфейса
        addrs = ip.get_addr(index=idx[0])
        
        if not addrs:
            print(f"[-] Интерфейс {TUN_IFACE} не имеет IP-адреса!")
            return None
            
        # Берем первый адрес (обычно он один у tun-интерфейса)
        tun_ip = addrs[0].get_attr('IFA_ADDRESS')
        tun_prefix = addrs[0]['prefixlen']
        return f"{tun_ip}/{tun_prefix}"
        
    finally:
        ip.close()

def tun_up():
    """Добавляет маршруты через tun0 интерфейс"""
    # Получаем текущий IP tun0
    tun_ip = get_tun_ip()
    if not tun_ip:
        print("[-] Не удалось определить IP tun0 интерфейса. Выход.")
        return 1
    
    print(f"[+] Найден интерфейс {TUN_IFACE} с IP {tun_ip}")
    
    # Загружаем конфигурацию маршрутов
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"[-] Файл конфигурации {CONFIG_FILE} не найден!")
        return 1
    
    # Сохраняем текущие маршруты
    save_routes()
    
    ip = IPRoute()
    try:
        # Добавляем маршруты из конфигурации
        for route in config.get("routes", []):
            try:
                route_kwargs = {
                    "dst": route["dst"],
                    "gateway": route.get("gateway", tun_ip.split('/')[0]),
                }
                if "metric" in route:
                    route_kwargs["priority"] = route["metric"]
                
                ip.route("add", **route_kwargs)
                print(f"[+] Добавлен маршрут: {route['dst']} через {route_kwargs['gateway']}" + 
                     (f" с метрикой {route['metric']}" if "metric" in route else ""))
            except Exception as e:
                print(f"[-] Ошибка добавления маршрута {route}: {e}")
    finally:
        ip.close()
    
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: sudo ./tun_route_manager.py <up|down>")
        sys.exit(1)
    
    if sys.argv[1] == "up":
        sys.exit(tun_up())
    elif sys.argv[1] == "down":
        sys.exit(restore_routes())
    else:
        print("Ошибка: допустимые аргументы — 'up' или 'down'")
        sys.exit(1)