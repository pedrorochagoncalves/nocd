# Original author: https://gist.github.com/kklimonda/890640

import gi.repository
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit', '3.0')
from gi.repository import Gtk, Gdk, WebKit


class BrowserTab(Gtk.VBox):
    def __init__(self, *args, **kwargs):
        super(BrowserTab, self).__init__(*args, **kwargs)

        self.webview = WebKit.WebView()
        self.show()

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.webview)

        find_box = Gtk.HBox()
        close_button = Gtk.Button("Close")
        close_button.connect("clicked", lambda x: find_box.hide())
        self.find_entry = Gtk.Entry()
        self.find_entry.connect("activate",
                                lambda x: self.webview.search_text(self.find_entry.get_text(),
                                                                   False, True, True))

        find_box.pack_start(close_button, False, False, 0)
        find_box.pack_start(self.find_entry, False, False, 0)
        self.find_box = find_box

        self.pack_start(scrolled_window, True, True, 0)
        self.pack_start(find_box, False, False, 0)

        scrolled_window.show_all()

    def load_url(self, url):
        if "://" not in url:
            url = "http://" + url
        print("Opening %s" % url)
        self.webview.load_uri(url)

    def get_html(self):
        self.webview.execute_script('oldtitle=document.title;document.title=document.documentElement.innerHTML;')
        html = self.webview.get_main_frame().get_title()
        self.webview.execute_script('document.title=oldtitle;')
        return html


class Browser(Gtk.Window):
    def __init__(self, *args, **kwargs):
        super(Browser, self).__init__(*args, **kwargs)

        # create notebook and tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)

        # basic stuff
        self.tabs = []
        self.fullscreen()

        # create a first, empty browser tab
        self.tabs.append((self._create_tab(), Gtk.Label("New Tab")))
        self.notebook.append_page(*self.tabs[0])
        self.add(self.notebook)

        # connect signals
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self._key_pressed)
        self.notebook.connect("switch-page", self._tab_changed)

        self.notebook.show()
        self.show()

    def _tab_changed(self, notebook, current_page, index):
        if not index:
            return
        title = self.tabs[index][0].webview.get_title()
        if title:
            self.set_title(title)

    def focus_tab(self, index):
        self.notebook.get_nth_page(index)

    def _title_changed(self, webview, frame, title):
        current_page = self.notebook.get_current_page()

        counter = 0
        for tab, label in self.tabs:
            if tab.webview is webview:
                label.set_text(title)
                if counter == current_page:
                    self._tab_changed(None, None, counter)
                break
            counter += 1

    def _create_tab(self):
        tab = BrowserTab()
        tab.webview.connect("title-changed", self._title_changed)
        return tab

    def reload_tab(self, index):
        self.tabs[index][0].webview.reload()

    def _close_current_tab(self):
        if self.notebook.get_n_pages() == 1:
            return
        page = self.notebook.get_current_page()
        current_tab = self.tabs.pop(page)
        self.notebook.remove(current_tab[0])

    def open_new_tab(self):
        current_page = self.notebook.get_current_page()
        page_tuple = (self._create_tab(), Gtk.Label("New Tab"))
        self.tabs.insert(current_page + 1, page_tuple)
        self.notebook.insert_page(page_tuple[0], page_tuple[1], current_page + 1)
        self.notebook.set_current_page(current_page + 1)

    def _focus_url_bar(self):
        current_page = self.notebook.get_current_page()
        self.tabs[current_page][0].url_bar.grab_focus()

    def _raise_find_dialog(self):
        current_page = self.notebook.get_current_page()
        self.tabs[current_page][0].find_box.show_all()
        self.tabs[current_page][0].find_entry.grab_focus()

    def _key_pressed(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        mapping = {Gdk.KEY_r: self.reload_tab,
                   Gdk.KEY_w: self._close_current_tab,
                   Gdk.KEY_t: self.open_new_tab,
                   Gdk.KEY_l: self._focus_url_bar,
                   Gdk.KEY_f: self._raise_find_dialog,
                   Gdk.KEY_q: Gtk.main_quit}

        if event.state & modifiers == Gdk.ModifierType.CONTROL_MASK \
                and event.keyval in mapping:
            mapping[event.keyval]()
