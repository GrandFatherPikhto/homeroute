#!/usr/bin/env python3
import json
import re
import sys
import socket
from collections import defaultdict

def extract_routes(openvpn_conf):
    """Извлекает маршруты из конфига OpenVPN"""
    routes = []
    route_regex = re.compile(r'^\s*route\s+([^\s]+)\s+([^\s]+)\s+(vpn_gateway|([^\s]+))')
    
    for line in openvpn_conf.splitlines():
        match = route_regex.match(line.strip())
        if match:
            target = match.group(1)
            netmask = match.group(2)
            gateway = match.group(4) if match.group(3) != 'vpn_gateway' else None
            
            # Если это доменное имя, разрешаем его в IP
            if not re.match(r'^\d+\.\d+\.\d+\.\d+$', target):
                try:
                    target_ip = socket.gethostbyname(target)
                    print(f"[+] Разрешено доменное имя {target} -> {target_ip}")
                    target = target_ip
                except socket.gaierror:
                    print(f"[-] Не удалось разрешить доменное имя {target}, пропускаем")
                    continue
            
            # Преобразуем в CIDR формат
            if netmask == '255.255.255.255':
                cidr = f"{target}/32"
            elif netmask == '255.255.255.0':
                cidr = f"{target}/24"
            elif netmask == '255.255.0.0':
                cidr = f"{target}/16"
            elif netmask == '255.0.0.0':
                cidr = f"{target}/8"
            else:
                # Для других масок просто используем оригинальный формат
                cidr = f"{target} {netmask}"
                print(f"[!] Нестандартная маска {netmask}, используем оригинальный формат")
            
            routes.append({
                "dst": cidr,
                "gateway": gateway,  # None будет заменено на tun_ip в основном скрипте
                "comment": f"Converted from: {line.strip()}"
            })
    
    return routes

def main(input_file, output_file):
    print(f"[*] Преобразование конфигурации OpenVPN из {input_file} в {output_file}")
    """Основная функция преобразования"""
    try:
        with open(input_file, 'r') as f:
            config_content = f.read()
    except FileNotFoundError:
        print(f"Ошибка: файл {input_file} не найден")
        return 1
    
    routes = extract_routes(config_content)
    
    # Создаем структуру конфига для tun_route_manager
    config = {
        "tun_ip": "10.109.154.78/21",  # По умолчанию, можно изменить вручную
        "routes": routes
    }
    
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print(f"Конфигурация успешно сохранена в {output_file}")
    print(f"Всего преобразовано {len(routes)} маршрутов")
    print("\nНе забудьте проверить и при необходимости изменить:")
    print(f"1. Параметр 'tun_ip' в {output_file}")
    print("2. Метрики маршрутов (добавить 'metric' при необходимости)")
    
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python convert_openvpn_routes.py <input.conf> <output.json>")
        sys.exit(1)
    
    sys.exit(main(sys.argv[1], sys.argv[2]))