import sys
from machine import Pin

# buzzer silent ASAP (boot.py does this too; belt and braces)
try:
    Pin(15, Pin.OUT, value=1)
except Exception:
    pass

try:
    held = open('/safety.flag').read().strip() == '1'
except Exception:
    held = False

if held:
    print('SAFETY MODE: UP was held at boot -> no HID installed.')
    print('Release UP and reset for a normal boot.')
else:
    try:
        import gunmouse
    except Exception as e:
        sys.print_exception(e)
    else:
        try:
            gunmouse.run()
        except KeyboardInterrupt:
            print('stopped by user')
        except Exception as e:
            print('RUNTIME FAULT:')
            sys.print_exception(e)
        finally:
            try:
                Pin(15, Pin.OUT, value=1)
            except Exception:
                pass
