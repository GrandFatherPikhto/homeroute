#!/usr/bin/env python3
from pyroute2 import IPRoute
import json
import sys
import os

FAKE_IFACE = "dummy0"
FAKE_IP = "10.95.3.100/24"
TEST_ROUTES = [
    {"dst": "192.168.100.0/24", "gateway": FAKE_IP.split("/")[0]},
    {"dst": "172.16.0.0/16", "gateway": FAKE_IP.split("/")[0]}
]
BACKUP_FILE = "./route_backup.json"

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

    ip = IPRoute()
    # Удаляем все маршруты (кроме основных, чтобы не потерять связь)
    for route in ip.get_routes():
        if route.get_attr("RTA_TABLE", 0) != 254:  # Пропускаем main table
            continue
        ip.route("del", **{
            "dst": route.get_attr("RTA_DST", ""),
            "gateway": route.get_attr("RTA_GATEWAY", ""),
            "oif": route.get_attr("RTA_OIF", ""),
        })

    # Восстанавливаем из резервной копии
    with open(BACKUP_FILE, "r") as f:
        routes = json.load(f)
    
    for route in routes:
        try:
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

def iface_up():
    """Создает фейковый интерфейс и добавляет тестовые маршруты."""
    save_routes()  # Сначала сохраняем текущие маршруты
    
    ip = IPRoute()
    print("[+] Создаю фейковый интерфейс...")
    ip.link("add", ifname=FAKE_IFACE, kind="dummy")
    idx = ip.link_lookup(ifname=FAKE_IFACE)[0]
    ip.addr("add", index=idx, address=FAKE_IP.split("/")[0], mask=24)
    ip.link("set", index=idx, state="up")

    for route in TEST_ROUTES:
        ip.route("add", dst=route["dst"], gateway=route["gateway"])
    
    ip.close()
    print("[+] Фейковый интерфейс и маршруты добавлены")

def iface_down():
    """Удаляет фейковый интерфейс и восстанавливает маршруты."""
    ip = IPRoute()
    idx = ip.link_lookup(ifname=FAKE_IFACE)
    if idx:
        ip.link("del", index=idx[0])
        print("[+] Фейковый интерфейс удален")
    ip.close()
    
    restore_routes()  # Восстанавливаем маршруты

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: sudo ./script.py <up|down>")
        sys.exit(1)
    
    if sys.argv[1] == "up":
        iface_up()
    elif sys.argv[1] == "down":
        iface_down()
    else:
        print("Ошибка: допустимые аргументы — 'up' или 'down'")
        