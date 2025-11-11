from PIL import Image
try:
    img = Image.open('/home/pi/pidisplay/icons/menu/menu_pressed.png')
    print('Loaded', img.size, img.mode, img.format)
except Exception as e:
    print('Failed:', str(e))