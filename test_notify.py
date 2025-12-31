import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify, GLib
import time

def on_action(notification, action_name, user_data):
    print(f"Action triggered: {action_name}")
    loop.quit()

Notify.init("Gaia Test")
n = Notify.Notification.new("Test Notification", "This is a test with an action", "dialog-information")
n.add_action("test_action", "Click Me", on_action, None)
n.set_hint("resident", GLib.Variant.new_boolean(True))
n.show()

print("Notification shown. Waiting 5 seconds or for action...")
loop = GLib.MainLoop()

# Set a timeout in case no action is clicked
GLib.timeout_add_seconds(5, loop.quit)
loop.run()
Notify.uninit()
