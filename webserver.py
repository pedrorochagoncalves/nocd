from flask import Flask
import random
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/bind-noc-display")
def bind_noc_display():

    # Generate random number to show on the screen. The user should send a request
    # with the number to bind the user to the display
    bind_number = random.randint(1, 1000)

    win = Gtk.Window()
    label = Gtk.Label(bind_number)
    win.add(label)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    app.run()