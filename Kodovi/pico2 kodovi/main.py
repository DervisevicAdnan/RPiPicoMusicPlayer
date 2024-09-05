import uos
import SDCard
from wavePlayer import wavePlayer
# mount SDCard
from machine import SPI,Pin,UART,Timer
import time
import asyncio
import machine
import _thread
import gc
import wave
print(machine.freq())
#machine.freq(200000000)
#print(machine.freq())
spi1 = SPI(1, baudrate=5_000_000, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
sd = SDCard.SDCard(spi1,Pin(13))

#sd.init_spi(50_000_000)

tim = Timer()

#need to pump up the SPI clock rate
# below 3MHz it won't work!
uos.mount(sd,"/sd")
pjesma = 0

player = wavePlayer()

waveFolder= "/sd"
wavelist = []

for i in uos.listdir(waveFolder):
    if i.find(".wav")>=0:
        wavelist.append(waveFolder+"/"+i)
    elif i.find(".WAV")>=0:
        wavelist.append(waveFolder+"/"+i)
        
uart1 = UART(0, baudrate=9600, tx=Pin(16), rx=Pin(17))

def pustiPjesmu(pin):
    global player, pjesma, wavelist
    if uart1.any():
        message = uart1.read().decode('utf-8')
        print('Received:', message)
        time.sleep(0.1)
        if "Play" in message:
            print("Plejaga")
            try:
                pjesma = int(message[5:])
                print("Pjeva: ",wavelist[pjesma])
                _thread.start_new_thread(player.play,([wavelist[pjesma]]))
            except KeyboardInterrupt:
                player.stop()
        elif message == "Resume":
                print("Resume")
                _thread.start_new_thread(player.continueSong,())

def ugasiPjesmu(timer):
    global player
    player.stop()
    
def pauzirajPjesmu(timer):
    global player
    player.pauseSong()

    
def nastaviPjesmu(timer):
    global player
    player.continueSong()

pokrenuto = False
timer = Timer()

def check_uart(pin):
    global wavelist, player, timer, pjesma, pokrenuto
    print("checkkkkkk")
    if uart1.any():
        message = uart1.read().decode('utf-8')
        print('Received:', message)
        time.sleep(0.1)
        if message == "Hello":
            uart1.write("start")
            time.sleep(1)
            for  i in wavelist:
                f = wave.open(i,'rb')
                rate = f.getframerate()
                frameCount = f.getnframes()
                vrijeme = frameCount/rate
                minute = vrijeme//60
                sekunde = str(int(vrijeme - minute * 60))
                if len(sekunde) < 2:
                    sekunde = "0" + sekunde
                uart1.write(i[4:-4]+","+str(int(minute))+":"+sekunde)
                time.sleep(0.2)
                gc.collect()
            gc.collect()
            uart1.write("end")
            time.sleep(0.1)

        elif message == "Stop":
            print("Stopaga")
            ugasiPjesmu(0)
            time.sleep(0.1)
        elif message == "Pause":
            print("Pauziramo")
            player.pauseSong()


rPin = Pin(18, Pin.IN)
rPin.irq(handler = check_uart, trigger = Pin.IRQ_RISING)
playPin = Pin(19, Pin.IN)
playPin.irq(handler = pustiPjesmu, trigger = Pin.IRQ_RISING)

try:
    for  i in wavelist:
        print(i)
except KeyboardInterrupt:
    player.stop()

while True:
    time.sleep(1)
