#!/usr/bin/env python3
import json
import re
import sys
import socket
import os
import ipaddress
from collections import defaultdict

class RouteConfig:
    """Извлекает маршруты из конфига OpenVPN"""
    routes = []
    
    def __init__ (self, config_file=None):
        self.counter = 0
        self.routes = []
        self.route_regex = re.compile(r'^\s*route\s+(?P<route>.*)')
        self.config_file = config_file
        self.check_config()
        self.config_content = None
        self.openvpn_conf()
        self.extract_routes()
        
    def __enter__ (self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        return False
                
    # Функция для проверки, является ли строка IP-адресом
    def is_ip(self, address):
        try:
            socket.inet_aton(address)
            return True
        except socket.error:
            return False

    def openvpn_conf(self):
        try:
            with open(self.config_file, 'r') as f:
                self.config_content = f.read()
        except FileNotFoundError:
            raise Exception(f"Ошибка: файл {self.config_file} не найден")
        
    
    def append_route(self, network: ipaddress.IPv4Network, metric=None, gateway='vpn_gateway'):
                
            route = {
                'network' : str(network),
                'address' : str(network.network_address),
                'netmask' : str(network.netmask),
                'metric' : metric,
                'gateway' : gateway,
                'comment' : ""
            }
            
            # print(f'[{self.counter + 1}]: {route["network"]}')
            self.routes.append(route)
            self.counter += 1


    
    def parse_route(self, conf: tuple):
        ipv4 = None
        if self.is_ip(conf[0]):
            try:
                ipv4 = ipaddress.IPv4Network(f'{conf[0]}/{conf[1]}')
            except ValueError as e:
                print(f'Это не IPV4 адрес {e}')
            except Exception as e:
                print(f'Ошибка: {e}')
                pass
            
        else:
            try:
                addr = socket.gethostbyname(conf[0])
                # print(f'Преобразование из доменного имени: {conf[0]}')
                # print(type(addr))
                ipv4 = ipaddress.IPv4Network(f'{addr}/{conf[1]}')
            except socket.gaierror as g:
                # print(f'Error: {g}')
                pass
            
        metric = None
        gateway = None
        
        if 'metric' in conf:
            idx = conf.index('metric')
            metric = conf[idx + 1]
            
        if 'vpn_gateway' in conf:
            gateway = 'vpn_gateway'
            
        if 'net_gateway' in conf:
            gateway = 'net_gateway'
            
        self.append_route(ipv4, metric, gateway)
            
    
    def extract_routes(self):
        if self.config_content != None:
            for line in self.config_content.splitlines():
                match = self.route_regex.match(line.strip())
                if match:
                    if match.group('route'):
                        route = match.group('route').split()
                        self.parse_route(route)

    def print_usage(self):
        print("Использование: python convert_openvpn_routes.py <input.conf> <output.json>")
        
    def check_config(self):
        if not os.path.exists(self.config_file):
            print(f"Такого файла {self.config_file} не существует")

def main(config_file):
    convert = RouteConfig (config_file=config_file)
    # print(len(convert.routes))

if __name__ == "__main__":    
    main('tun_routes.conf')
