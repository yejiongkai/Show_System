echo 496 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio496/direction
sudo chmod 777 /sys/class/gpio/gpio496/direction
sudo chmod 777 /sys/class/gpio/gpio496/value
echo 445 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio445/direction
sudo chmod 777 /sys/class/gpio/gpio445/direction
sudo chmod 777 /sys/class/gpio/gpio445/value
sudo chmod 777 /dev/ttyAMA2
sudo -u user
cd work/Pi
python3 server_system.py