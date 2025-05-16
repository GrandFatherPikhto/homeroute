import subprocess
import json
from datetime import datetime
import os
from pathlib import Path

class WriteRoutes:

    def __init__(self, output_dir='out', interface=None):
        #self.current_dir = os.getcwd()
        self.interface=interface
        self.output_dir=os.path.join(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        
        if self.interface == None:
            self.route_file=os.path.join(self.output_dir, 'all_' + datetime.now().strftime('%Y%m%d%H%M%S') + '.json')
        else:
            self.route_file=os.path.join(self.output_dir, interface + '_' + datetime.now().strftime('%Y%m%d%H%M%S') + '.json')
        
        self.save_routes_to_file()
            
    def save_routes_to_file(self):
        """
        Сохраняет таблицу маршрутизации в JSON-файл
        :param output_file: Путь к выходному файлу
        :param interface: Фильтр по интерфейсу (например, 'tun0')
        """
        # Получаем маршруты через ip route
        result = subprocess.run(['ip', 'route', 'show'], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Ошибка: {result.stderr}")
            return

        # Парсим вывод
        routes = []
        for line in result.stdout.splitlines():
            if self.interface and f"dev {self.interface}" not in line:
                continue
                
            parts = line.split()
            route = {
                'destination': 'default' if 'default' in parts else parts[0],
                'via': parts[parts.index('via') + 1] if 'via' in parts else None,
                'dev': parts[parts.index('dev') + 1] if 'dev' in parts else None,
                'metric': int(parts[parts.index('metric') + 1]) if 'metric' in parts else None,
                'raw': line
            }
            routes.append(route)

        # Добавляем метаданные
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_routes': len(routes),
            'routes': routes
        }

        # Сохраняем в файл
        with open(self.route_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Сохранено {len(routes)} маршрутов в {self.route_file}")


# Пример использования
if __name__ == "__main__":
    routes = WriteRoutes()
    routes_tun = WriteRoutes(interface='tun0')
    # Все маршруты
    #save_routes_to_file("all_routes.json")
    
    # Только маршруты через tun0 (OpenVPN)
    #save_routes_to_file("vpn_routes.json", interface="tun0")