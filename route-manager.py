#!/usr/bin/env python
from pyroute2 import IPRoute
import argparse
import json
import sys
import os

import rconfig

# pyinstaller --onefile route-manager.py

BACKUP_FILE="./route_backup.json"
CURRENT_ROUTES_FILE="./current_routes.json"

class RouteManager:
    def __init__ (self, config_file: str, iface_name: str = 'tun0',  backup_file: str = BACKUP_FILE, current_routes_file:str = CURRENT_ROUTES_FILE):
        self.config_file = config_file
        with rconfig.RouteConfig(config_file) as config:
            self.routes = config.routes
        self.current_routes = []
        self.iface_name = iface_name
        self.backup_file = backup_file
        self.current_routes_file = current_routes_file
        self.ip_route = IPRoute()
        
    def __enter__ (self):
        """Нужно для обработки with"""
        return self
    
    def __exit__ (self, exc_type, exc_value, traceback):
        """Заканчиваем работу класса"""
        self.close()
        return False
    
    def get_interface_ip(self, iface_name):
        """Получает IP-адрес tun0 интерфейса"""
        self.iface_name = iface_name
        try:
            # Ищем интерфейс tun0
            idx = self.ip_route.link_lookup(ifname=self.iface_name)
            if not idx:
                print(f"[-] Интерфейс {self.iface_name} не найден!")
                return None
            
            # Получаем все адреса интерфейса
            addrs = self.ip_route.get_addr(index=idx[0])
            
            if not addrs:
                print(f"[-] Интерфейс {self.iface_name} не имеет IP-адреса!")
                return None
                
            # Берем первый адрес (обычно он один у tun-интерфейса)
            tun_ip = addrs[0].get_attr('IFA_ADDRESS')
            tun_prefix = addrs[0]['prefixlen']
            self.iface_ip = f'{tun_ip}/{tun_prefix}'
            
            print(f"[+] Интерфейс {self.iface_name}: {self.iface_ip}")
            
            return self.iface_ip
        
        except Exception as e:
            print('Ошибка {e}')
            return None            

    def save_current_routes(self):
        """Сохраняет текущие маршруты в файл."""
        try:
            with open(self.current_routes_file, "w") as f:
                # print(self.current_routes)
                json.dump(self.current_routes, f, indent=4)
        except OSError as e:
            print(f'Ошибка открытия файла: {e}')

        print(f"[+] Сохранено {len(self.current_routes)} маршрутов в {BACKUP_FILE}")
        
    def load_current_routes(self):
        """Восстанавливает маршруты из файла."""
        if not os.path.exists(self.current_routes_file):
            print("[-] Файл с резервной копией маршрутов не найден!")
            return
        with open(self.current_routes_file, 'r') as f:
            self.current_routes = json.load(f)
        

    def add_routes(self):
        """Добавляет маршруты к интерфейсу {self.iface_name}"""
        counter = 0
        for route in self.routes:
            gateway = self.iface_ip
            if route['gateway'] != 'vpn_gateway':
                gateway = route['gateway']
            try:
                self.ip_route.route("add", dst=route["network"], gateway=gateway)
                # print(res)
                print(f"[+] Добавлен маршрут {route['network']} через {self.iface_name}")
                self.current_routes.append(route)
                counter += 1
            except Exception as e:
                print(f'[-] Ошибка добавления маршрута: {e}')
                    
        self.save_current_routes()
        print(f"[+] Добавлено {counter} маршрутов к {self.iface_name}")
        
                    
    def remove_routes(self):
        """Удаляет маршруты из интерфейса {self.iface_name}"""
        counter = 0
        if os.path.exists(self.current_routes_file):
            self.load_current_routes()
        else:
            self.current_routes = self.routes
            
        for route in self.current_routes:
            if route['gateway'] == 'vpn_gateway':
                try:
                    res = self.ip_route.route("del", dst=route["network"], gateway=self.iface_ip)
                    print(f"[+] Удалён маршрут {route['network']} через {self.iface_name}")
                    # print(res)
                    counter += 1
                except Exception as e:
                    print(f"[-] Ошибка удаления маршрута {route['network']}: {e}")
                    continue
        print(f"[+] Удалено {counter} маршрутов из {self.iface_name}")                    

            
    def check_interface_exists(self, interface_name):
        try:
            # Получаем список всех доступных интерфейсов
            interfaces = self.ip_route.get_links()

            # Ищем среди интерфейсов тот, у которого имя совпадает
            for iface in interfaces:
                ifname = iface.get_attr('IFLA_IFNAME')
                if ifname == interface_name:
                    return True  # Интерфейс существует

            return False  # Интерфейс не найден
        except Exception as e:
            return False
    
    def close(self):
        self.ip_route.close()
        
def main():
    # Создаем парсер аргументов
    parser = argparse.ArgumentParser(description="Добавление и удаление маршрутов интерфейса")

    # Добавляем аргумент up/down (позиционный)
    parser.add_argument(
        "state",
        choices=["up", "down", "reload"],  # Ограничиваем только значениями up или down
        help="Состояние интерфейса (up или down). Пример: up"
    )
    
    # Добавляем обязательный аргумент config с format config=<file>
    parser.add_argument(
        "--config", required=True, type=str, help="Путь к файлу конфигурации. Пример: --config=routes.conf"
    )

    # Добавляем обязательный аргумент interface с format interface=<name>
    parser.add_argument(
        "interface", type=str, help="Имя интерфейса. Пример: tun0"
    )
    
    # tun0 1500 0 10.109.154.78 255.255.248.0 init
    # parser.add_argument("iface", type=str, nargs='*', help="Интерфейс, который может передавать openvpn")
    parser.add_argument("MTU", nargs='*', help="MTU (Maximum Transmission Unit) интерфейса.")
    parser.add_argument("metric", nargs='*', help="Метрика маршрута")
    parser.add_argument("local-ip", nargs='*', help="Локальный IP-адрес интерфейса")
    parser.add_argument("netmask", nargs='*', help="Маска подсети")
    parser.add_argument("regime", nargs='*', help="Режим инициализации (может быть init или restart).")

    # Разобираем аргументы
    args = parser.parse_args()

    # Выводим результаты
    print(f"Имя интерфейса: {args.interface}")
    print(f"Состояние: {args.state}")
    print(f"Файл конфигурации: {args.config}")
    
    with RouteManager(config_file=args.config) as manager:
        res = manager.get_interface_ip(args.interface)
        if res:
            if args.state == 'up':
                manager.add_routes()
            elif args.state == 'down':
                manager.remove_routes()
            elif args.state == 'reload':
                manager.remove_routes()
                manager.add_routes ()
        
if __name__ == '__main__':
    """
        ./route_manager.py up --config=tun_routes.conf tun0
        ./route_manager.py down --config=tun_routes.conf tun0
    """
    print(sys.argv)
    main()
