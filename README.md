# Скрипт для настройки роутинга на домашнем роутере

Этот скрипт предназначен для правки маршрутизации идущей через tun0 (openvpn)

## Синтаксис конфигурационного файла
Такой же, как у openvpn:

```
route <network/doman_name/ip_address> <netmask> <gateway>
```

gateway может принимать (пока) только либо vpn_gateway (указанный интерфейс), либо IP адресс

Например:

```
route 188.114.99.232 255.255.255.255 vpn_gateway
```


## Командная строка

```
./route-manager.py up|down|reload --config=<имя_конфигурационного_файла> <имя_интерфейса>
```

Например:

```
./route-manager.py reload --config=routes.conf tun0
```

## Компиляция для запуска при старте openvpn

```
pyinstaller --onefile route-manager.py
```

## Конфигурационный файл openvpn

Рекомендуется положить скомпилированный файл например, в директорию /opt/openvpn

```
# Отключаем маршрутизацию _всего_ трафика через tun0
route-nopull

# Явно указываем маршрут для локальной сети через физический интерфейс
route 10.95.2.0 255.255.255.192 metric 600  # Указываем высокий metric

script-security 2
route-up "/opt/openvpn/route-manager up --config=/etc/openvpn/routes.conf tun0"
route-pre-down "/opt/openvpn/route-manager down --config=/etc/openvpn/routes.conf"

status /var/log/openvpn/traffic.log 5
```

- ```route 10.95.2.0 255.255.255.192 metric 600``` нужен для того, чтобы была маршрутизация по умолчанию, не через tun0
- ```route-pre-down``` самопроизвольно передаёт первым аргументом имя интерфейса, к примеру ```tun0```
- ```route-up``` этого не делает, поэтому надо передавать имя интерфейса _явно_

# Команды tasks для VSCode

F1=>Tasks:Run Task
- Reload Route Manager
- Build With PyInstaller

# Команда разрешения работы скрипта из под пользователя

1. Дать разрешение python3:
    ```sudo setcap cap_net_admin+eip $(readlink -f $(which python3))```

2. Создать специальную группу и дать права:

```bash
# Создаем новую группу
sudo groupadd netadmin

# Добавляем пользователя в группу
sudo usermod -aG netadmin ваш_пользователь

# Назначаем права на сетевые интерфейсы
sudo chgrp netadmin /sys/class/net/
sudo chmod g+rw /sys/class/net/
```