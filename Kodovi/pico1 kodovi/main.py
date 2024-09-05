import lvgl as lv
from machine import Pin, Timer, SPI, UART
import ili9xxx
import gc
import uos
import time
import _thread

DEBOUNCE_TIME = 200 # u ms
last_button_press_time = 0

uart1 = UART(0, baudrate=9600, tx=Pin(12), rx=Pin(13))

spi = SPI(0, baudrate=50_000_000, sck=Pin(18), mosi=Pin(19), miso=Pin(16))

drv = ili9xxx.Ili9341(spi=spi, dc=15, cs=17, rst=20)

gc.collect()
songList = [] # Lista ucitanih pjesama

trigg = Pin(11,Pin.OUT)
trigPlay = Pin(15,Pin.OUT)

gc.enable()
width = 320
height = 240
currentButton = None
currentSongIndex = 0

sviraPjesma = False
pauzirano = False
ucitanePjesme = False

trajanjePjesme = 1
prosloPjesme = 0

mode = 'Welcome'
# Mogući modovi su:
# Welcome - početni ekran koji se prikazuje samo pri prvom pokretanju playera
# List - ekran koji prikazuje listu svih pjesama, tu se može odabrati pjesma skrolanjem kroz listu pomoću enkodera
# Song - ekran na kojem se nalazi ime pjesme koja se trenutno emitira, vrijeme trajanja, progress bar

print("Učitane pjesme:\n")
while not ucitanePjesme:
    uart1.write('Hello')
    time.sleep(2)
    
    trigg.value(1)
    time.sleep(1)
    trigg.value(0)
    
    if uart1.any():
        message = uart1.read().decode('utf-8')
        if message == "start":
            while True:
                if uart1.any():
                    message = uart1.read().decode('utf-8')
                    if message == "end":
                        ucitanePjesme = True
                        break
                    songList.append(message.split(","))
                    print(songList[-1][0]," - ",songList[-1][1])
                time.sleep(0.2)
            break
    time.sleep(1)



clk = Pin(4, Pin.IN)
dt = Pin(5, Pin.IN)
sw = Pin(14, Pin.IN)

clk_okinut = dt_okinut = smjer = False
# Okinuti su kad predju sa High na Low
# Za smjer True je desno, a False je lijevo

prva_prikazana_pjesma = 0
zadnja_prikazana_pjesma = 6

# Funkcija koja ažurira vrijednost na progress baru
def update_bar(timer):
    global trajanjePjesme, prosloPjesme
    prosloPjesme += 1
    bar.set_value(int((prosloPjesme / trajanjePjesme) * 100), lv.ANIM.ON)
    dur_label.set_text("{:02d}:{:02d}".format(prosloPjesme // 60, prosloPjesme % 60))
    if prosloPjesme > trajanjePjesme:
        nextSong(0)
    
timer = Timer()

def changeToList(pin):
    global tv,tile2,mode,sviraPjesma,pauzirano,tipke,currentSongIndex,prva_prikazana_pjesma, selectedTrackStyle,trackStyle, timer, DEBOUNCE_TIME, last_button_press_time
    # Debouncing
    tmp = last_button_press_time
    current_time = time.ticks_ms()
    last_button_press_time = current_time
    if time.ticks_diff(current_time, tmp) < DEBOUNCE_TIME:
        return
    
    if sviraPjesma and not pauzirano:
        stopSong()
    sviraPjesma = False
    pauzirano = False
    mode = 'List'
    postaviNaPocetak()
    tipke[currentSongIndex - prva_prikazana_pjesma].replace_style(trackStyle,selectedTrackStyle,0)
    tv.set_tile(tile2,lv.ANIM.OFF)
    gc.collect()

def playSong(pin):
    global songList, sviraPjesma, currentSongIndex, mode, pauzirano, timer, prosloPjesme, DEBOUNCE_TIME, last_button_press_time
    # Debouncing
    tmp = last_button_press_time
    current_time = time.ticks_ms()
    last_button_press_time = current_time
    if time.ticks_diff(current_time, tmp) < DEBOUNCE_TIME:
        return
    
    if mode == 'Welcome':
        return
    changeToSong(pin)
    gc.collect()
    if not sviraPjesma:
        uart1.write('Play ' + str(currentSongIndex))
        prosloPjesme = 0
        sviraPjesma = True
        pauzirano = False
        time.sleep(2)
        timer.init(callback = update_bar, period = 1000, mode = Timer.PERIODIC)
        trigPlay.value(1)
        time.sleep(1)
        trigPlay.value(0)
        print("Puštam pjesmu\n")
    elif pauzirano:
        uart1.write('Resume')
        pauzirano = False
        time.sleep(2)
        timer.init(callback = update_bar, period = 1000, mode = Timer.PERIODIC)
        trigPlay.value(1)
        time.sleep(1)
        trigPlay.value(0)
        print("Puštam pjesmu\n")
    else:
        uart1.write('Pause')
        pauzirano = True
        time.sleep(2)
        timer.deinit()
        trigg.value(1)
        time.sleep(1)
        trigg.value(0)
        print("Pauziram pjesmu\n")
        
def stopSong():
    global timer, uart1, sviraPjesma, pauzirano, trigg
    timer.deinit()
    uart1.write('Stop')
    sviraPjesma = False
    pauzirano = False
    time.sleep(2)
    trigg.value(1)
    time.sleep(1)
    trigg.value(0)
    print("Zaustavljam pjesmu\n")
    
def changeToSong(pin):
     global tv,tile3,label1,currentSongIndex, mode, songList, prva_prikazana_pjesma,selectedTrackStyle,trackStyle, trajanjePjesme, prosloPjesme, dur_labelMax
     if mode != 'Welcome':
         if mode == 'List':
             tipke[currentSongIndex - prva_prikazana_pjesma].replace_style(selectedTrackStyle,trackStyle,0)
         mode = 'Song'
         vr = songList[currentSongIndex][1].split(":")
         trajanjePjesme = int(vr[0]) * 60 + int(vr[1])
         
         label1.set_text(songList[currentSongIndex][0])
         dur_labelMax.set_text(songList[currentSongIndex][1])
         tv.set_tile(tile3,lv.ANIM.ON)
         gc.collect()

def postaviNaPocetak():
    global tipke, songList, list, currentSongIndex, prva_prikazana_pjesma, zadnja_prikazana_pjesma
    if len(songList) < 8:
        currentSongIndex = prva_prikazana_pjesma
        return
    prva_prikazana_pjesma = 0
    zadnja_prikazana_pjesma = min(6, len(songList))
    for btn_counter in range(7):
        list.set_button_text(tipke[btn_counter], songList[btn_counter][0])
    currentSongIndex = prva_prikazana_pjesma
    
def postaviNaKraj():
    global tipke, songList, list, currentSongIndex, prva_prikazana_pjesma, zadnja_prikazana_pjesma
    if len(songList) < 8:
        currentSongIndex = zadnja_prikazana_pjesma
        return
    prva_prikazana_pjesma = max(0, len(songList)-7)
    zadnja_prikazana_pjesma = len(songList) - 1
    for btn_counter in range(7):
        list.set_button_text(tipke[btn_counter], songList[prva_prikazana_pjesma + btn_counter][0])
    currentSongIndex = zadnja_prikazana_pjesma
    
def pomjeriGore():
    global tipke, songList, list, currentSongIndex, prva_prikazana_pjesma, zadnja_prikazana_pjesma
    prva_prikazana_pjesma += 1
    zadnja_prikazana_pjesma += 1
    for btn_counter in range(7):
        list.set_button_text(tipke[btn_counter], songList[btn_counter + prva_prikazana_pjesma][0])
    currentSongIndex = zadnja_prikazana_pjesma

def pomjeriDolje():
    global tipke, songList, list, currentSongIndex, prva_prikazana_pjesma, zadnja_prikazana_pjesma
    prva_prikazana_pjesma -= 1
    zadnja_prikazana_pjesma -= 1
    for btn_counter in range(7):
        list.set_button_text(tipke[btn_counter], songList[btn_counter + prva_prikazana_pjesma][0])
    currentSongIndex = prva_prikazana_pjesma

def nextSong(pin):
    global currentSongIndex, songList, tipke, mode, DEBOUNCE_TIME, last_button_press_time, prva_prikazana_pjesma, zadnja_prikazana_pjesma, pauzirano, sviraPjesma, timer
    # Debouncing
    tmp = last_button_press_time
    current_time = time.ticks_ms()
    last_button_press_time = current_time
    if time.ticks_diff(current_time, tmp) < DEBOUNCE_TIME:
        return
    
    if mode == 'List':
        tipke[currentSongIndex - prva_prikazana_pjesma].replace_style(selectedTrackStyle,trackStyle,0)
        if currentSongIndex + 1 == len(songList):
            postaviNaPocetak()
        elif currentSongIndex == zadnja_prikazana_pjesma and zadnja_prikazana_pjesma + 1 < len(songList):
            pomjeriGore()
        else:
            currentSongIndex = currentSongIndex + 1
        tipke[currentSongIndex - prva_prikazana_pjesma].replace_style(trackStyle,selectedTrackStyle,0)
        gc.collect()
    elif mode == 'Song':
        if sviraPjesma and not pauzirano:
            stopSong()
        else:
            sviraPjesma = False
            pauzirano = False
        currentSongIndex = (currentSongIndex + 1) % len(songList)
        changeToSong(pin)
        playSong(pin)
        pass
        
    
def prevSong(pin):
    global currentSongIndex, songList, mode, DEBOUNCE_TIME, last_button_press_time, prva_prikazana_pjesma, zadnja_prikazana_pjesma, sviraPjesma, pauzirano, timer
    # Debouncing
    tmp = last_button_press_time
    current_time = time.ticks_ms()
    last_button_press_time = current_time
    if time.ticks_diff(current_time, tmp) < DEBOUNCE_TIME:
        return
    
    if mode == 'List':
        tipke[currentSongIndex - prva_prikazana_pjesma].replace_style(selectedTrackStyle,trackStyle,0)
        
        if currentSongIndex == 0:
            postaviNaKraj()
        elif currentSongIndex == prva_prikazana_pjesma and prva_prikazana_pjesma > 0:
            pomjeriDolje()
        else:
            currentSongIndex = currentSongIndex - 1

        tipke[currentSongIndex - prva_prikazana_pjesma].replace_style(trackStyle,selectedTrackStyle,0)
        gc.collect()
    elif mode == 'Song':
        if sviraPjesma and not pauzirano:
            stopSong()
        else:
            sviraPjesma = False
            pauzirano = False
        currentSongIndex = currentSongIndex - 1
        if currentSongIndex < 0:
            currentSongIndex = len(songList) - 1
        changeToSong(pin)
        playSong(pin)

def okinutCLK(pin):
  global clk_okinut, dt_okinut
  clk_okinut = True
  if dt_okinut:
    nextSong(pin)
    clk_okinut = dt_okinut = False

def okinutDT(pin):
  global clk_okinut, dt_okinut
  dt_okinut = True
  if clk_okinut:
    prevSong(pin)
    clk_okinut = dt_okinut = False

clk.irq(trigger=Pin.IRQ_FALLING, handler=okinutCLK)
dt.irq(trigger=Pin.IRQ_FALLING, handler=okinutDT)
sw.irq(trigger=Pin.IRQ_FALLING, handler=changeToSong)

# naprijed(clockwise): CLK pa DT
# nazad(counter clockwise): DT pa CLK

# Kreiranje 2x2 tileview-a i omogućavanje skrolanja u obliku slova "L".
tv = lv.tileview(lv.screen_active())

tvStyle = lv.style_t()
tvStyle.init()
tvStyle.set_border_width(0)

tile1 = tv.add_tile(0, 0, lv.DIR.BOTTOM)

s1_1=lv.style_t()
s1_1.init()
s1_1.set_radius(0)
s1_1.set_bg_color(lv.color_hex(0x311B92))
s1_1.set_bg_grad_color(lv.color_hex(0xD1C4E9))
s1_1.set_bg_grad_dir(lv.GRAD_DIR.VER)
s1_1.set_border_width(0)

t1_1=lv.obj(tile1)
t1_1.set_size(335,125)
t1_1.align(lv.ALIGN.TOP_MID,0,-5)
t1_1.add_style(s1_1,0)

s1_2=lv.style_t()
s1_2.init()
s1_2.set_radius(0)
s1_2.set_bg_color(lv.color_hex(0xD1C4E9))
s1_2.set_bg_grad_color(lv.color_hex(0x311B92))
s1_2.set_bg_grad_dir(lv.GRAD_DIR.VER)
s1_2.set_border_width(0)

t1_2=lv.obj(tile1)
t1_2.set_size(335,125)
t1_2.align(lv.ALIGN.BOTTOM_MID,0,5)
t1_2.add_style(s1_2,0)

# Učitavanje slike u 'Welcome' modu
with open('/etf_logo.png', 'rb') as f:
  png_data = f.read()

png_image_dsc = lv.image_dsc_t({
    'data_size': len(png_data),
    'data': png_data 
})

# Kreiraj sliku korištenjem dekodera
image1 = lv.image(tile1)
image1.set_src(png_image_dsc)
image1.center()
image1.set_scale(500)

# Tile 2 
tile2 = tv.add_tile(0, 1, lv.DIR.TOP | lv.DIR.RIGHT)

styleBG= lv.style_t()
styleBG.init()
styleBG.set_bg_color(lv.color_hex(0x000000))

listStyle=lv.style_t()
listStyle.init()
listStyle.set_border_width(0)

list = lv.list(tile2)
list.set_size(lv.pct(110), lv.pct(100))
list.center()
list.add_style(listStyle,0)

# Stil svih pjesama u listi
trackStyle = lv.style_t()
trackStyle.init()
trackStyle.set_bg_color(lv.color_hex(0x311B92))
trackStyle.set_bg_grad_color(lv.color_hex(0x7E57C2))
trackStyle.set_bg_grad_dir(lv.GRAD_DIR.HOR)
trackStyle.set_border_color(lv.color_hex(0x9575CD))
trackStyle.set_border_width(1)
trackStyle.set_border_side(lv.BORDER_SIDE.BOTTOM | lv.BORDER_SIDE.TOP )
trackStyle.set_text_color(lv.color_hex(0xD1C4E9))

# Stil selektovane pjesme u listi
selectedTrackStyle = lv.style_t()
selectedTrackStyle.init()
selectedTrackStyle.set_bg_color(lv.color_hex(0x7E57C2))
selectedTrackStyle.set_bg_grad_color(lv.color_hex(0x5E35B1))
selectedTrackStyle.set_bg_grad_dir(lv.GRAD_DIR.HOR)
selectedTrackStyle.set_border_color(lv.color_hex(0xE0F7FA))
selectedTrackStyle.set_border_width(1)
selectedTrackStyle.set_border_side(lv.BORDER_SIDE.BOTTOM | lv.BORDER_SIDE.TOP )
selectedTrackStyle.set_text_color(lv.color_hex(0xFFFFFF))

# Stil note koja se prikazuje u 'Song' modu dok pjesma svira
notaStyle = lv.style_t()
notaStyle.init()
notaStyle.set_bg_opa(lv.OPA._30)

tipke = []

# Inicijalizacija liste koja sadrzi sve 'tipke' tj. pjesme
for btn_counter in range(7):
    btn = list.add_button(lv.SYMBOL.AUDIO, "")
    zadnja_prikazana_pjesma = min(6,len(songList)-1)
    if btn_counter < len(songList):
        list.set_button_text(btn,songList[btn_counter][0])
    tipke.append(btn)
    if btn_counter == 0:
        btn.add_style(selectedTrackStyle,0)
    else:
        btn.add_style(trackStyle,0)
    if btn_counter == 0:
        currentButton = btn

gc.collect()

# Tile3 je tile koji se prikazuje u 'Song' modu
tile3 = tv.add_tile(1, 1, lv.DIR.LEFT)

s3_1=lv.style_t()
s3_1.init()
s3_1.set_radius(0)
s3_1.set_bg_color(lv.color_hex(0x311B92))
s3_1.set_bg_grad_color(lv.color_hex(0xD1C4E9))
s3_1.set_bg_grad_dir(lv.GRAD_DIR.VER)
s3_1.set_border_width(0)

t3_1=lv.obj(tile3)
t3_1.set_size(335,125)
t3_1.align(lv.ALIGN.TOP_MID,0,-5)
t3_1.add_style(s3_1,0)

gc.collect()

s3_2=lv.style_t()
s3_2.init()
s3_2.set_radius(0)
s3_2.set_bg_color(lv.color_hex(0xD1C4E9))
s3_2.set_bg_grad_color(lv.color_hex(0x311B92))
s3_2.set_bg_grad_dir(lv.GRAD_DIR.VER)
s3_2.set_border_width(0)

t3_2=lv.obj(tile3)
t3_2.set_size(335,125)
t3_2.align(lv.ALIGN.BOTTOM_MID,0,5)
t3_2.add_style(s3_2,0)

# Bijeli okvir oko slike note
okvir=lv.obj(tile3)
okvir.set_size(4*35,3*35)
okvir.align(lv.ALIGN.CENTER,0,-30)
okvirLabel=lv.label(okvir)
okvirLabel.set_text(lv.SYMBOL.AUDIO)
okvirLabel.set_style_text_font(lv.font_montserrat_24,0)
okvir.add_style(notaStyle,0)

okvirLabel.center()

label1 = lv.label(tile3)
label1.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)         
label1.set_width(200)
label1.align(lv.ALIGN.CENTER, 0, 80)
songTextStyle=lv.style_t()
songTextStyle.init()
songTextStyle.set_text_color(lv.color_hex(0x311B92))


# Stilizacija progress bara u 'Song' modu
style_bg = lv.style_t()
style_indic = lv.style_t()
style_knob = lv.style_t()

style_bg.init()
style_bg.set_border_color(lv.color_hex(0xFFFFFF))
style_bg.set_border_width(1)
style_bg.set_pad_all(0)
style_bg.set_radius(50)
style_bg.set_anim_duration(1000)


style_indic.init()
style_indic.set_bg_opa(lv.OPA.COVER)
style_indic.set_bg_color(lv.color_hex(0x311B92))
style_indic.set_radius(3)

style_knob.init()
style_knob.set_bg_color(lv.color_hex(0xFFFFFF))
style_knob.set_radius(lv.RADIUS_CIRCLE)
style_knob.set_pad_all(2)

bar = lv.slider(tile3)
bar.add_style(style_bg, lv.PART.MAIN)
bar.add_style(style_indic, lv.PART.INDICATOR)
bar.add_style(style_knob,lv.PART.KNOB)

bar.set_size(200, 5)
bar.set_range(0, 100)
bar.align(lv.ALIGN.CENTER, 0, 50)
bar.set_value(0, lv.ANIM.ON)

# Labele za prikaz vremena
dur_label = lv.label(tile3)
dur_label.set_width(50)
dur_label.set_text("0.00")
dur_label.align(lv.ALIGN.CENTER, -125, 50)

dur_labelMax = lv.label(tile3)
dur_labelMax.set_width(50)
dur_labelMax.set_text("5.19")
dur_labelMax.align(lv.ALIGN.CENTER, 135, 50)

gc.collect()

# Inicijalizacija prekida na 4 korištena tastera
btn1 = Pin(0,Pin.IN)
btn1.irq(trigger=Pin.IRQ_FALLING, handler=changeToList)

btn2 = Pin(1,Pin.IN)
btn2.irq(trigger=Pin.IRQ_FALLING, handler=playSong)

btn3 = Pin(2,Pin.IN)
btn3.irq(trigger=Pin.IRQ_FALLING, handler=prevSong)

btn4 = Pin(3,Pin.IN)
btn4.irq(trigger=Pin.IRQ_FALLING, handler=nextSong)