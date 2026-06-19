import usb_hid
import usb_midi
import usb_cdc

usb_hid.disable()
usb_midi.disable()
usb_cdc.enable(console=True, data=True)
