#!/usr/bin/env python3
from pyroute2 import IPRoute
import sys

FAKE_IFACE = "dummy0"
FAKE_IP = "10.95.3.100/24"
TEST_ROUTES = [
    {"dst": "192.168.100.0/24", "gateway": FAKE_IP.split("/")[0]},
    {"dst": "172.16.0.0/16", "gateway": FAKE_IP.split("/")[0]}
]

def iface_up():
    """Создает интерфейс и маршруты через pyroute2."""
    ip = IPRoute()
    print("[+] Создаю фейковый интерфейс...")
    
    # Создаем dummy-интерфейс
    ip.link("add", ifname=FAKE_IFACE, kind="dummy")
    idx = ip.link_lookup(ifname=FAKE_IFACE)[0]
    
    # Добавляем IP-адрес
    ip.addr("add", index=idx, address=FAKE_IP.split("/")[0], mask=24)
    ip.link("set", index=idx, state="up")
    
    # Добавляем маршруты
    for route in TEST_ROUTES:
        ip.route("add", dst=route["dst"], gateway=route["gateway"])
    
    print("[+] Готово!")
    ip.close()

def iface_down():
    """Удаляет интерфейс (маршруты удалятся автоматически)."""
    ip = IPRoute()
    print("[+] Удаляю фейковый интерфейс...")
    
    idx = ip.link_lookup(ifname=FAKE_IFACE)
    if idx:
        ip.link("del", index=idx[0])
    
    print("[+] Готово!")
    ip.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: ./script.py <up|down>")
        sys.exit(1)
    
    if sys.argv[1] == "up":
        iface_up()
    elif sys.argv[1] == "down":
        iface_down()
    else:
        print("Ошибка: допустимые аргументы — 'up' или 'down'")
