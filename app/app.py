import sys, os
from PyQt5.QtCore import Qt, QRectF, QPointF, QSize, QTimer
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPixmap
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QFrame, QVBoxLayout,
                             QHBoxLayout, QStackedWidget, QSizePolicy, QPushButton)

import tokens as T
import ui
import data as datamod
from ui import (PaintWidget, IconButton, Text, Card, NavTab, SubNavItem, Divider,
                SliderRow, Sparkline, StatTile, app_font, rgba,
                i_gear, i_user, i_desktop, i_grid, i_list, i_crosshair,
                i_logo, i_back, i_battery)

HERE = os.path.dirname(os.path.abspath(__file__))

# The live telemetry channel.  Leave the dictionary empty to fall back to the
# synthetic source, which keeps the interface usable with no network at all.
THINGSPEAK = {"channel": "3541064", "read_key": "35YX48TUIJDYNUQ6"}


def default_source():
    if THINGSPEAK.get("channel") and THINGSPEAK.get("read_key"):
        return datamod.make_source("cloud", **THINGSPEAK)
    return datamod.make_source("mock")


# ============ device card ============

class DeviceCard(ui.Card):
    clicked = None

    def __init__(self, parent=None):
        super().__init__(T.RADIUS_LG, T.SURFACE, parent)
        self.setFixedSize(T.CARD_W, T.CARD_H)
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(T.CARD_PAD, 30, T.CARD_PAD, 0)
        lay.setSpacing(0)

        name = Text("PICO GUN\nMOUSE", 19.0, True)
        name.setWordWrap(True)
        name.setMaximumHeight(160)
        lay.addWidget(name)

        lay.addSpacing(10)
        row = QWidget(); row.setStyleSheet("background:transparent;")
        rl = QHBoxLayout(row); rl.setContentsMargins(0, 2, 0, 0); rl.setSpacing(T.GAP_STATUS)
        self.pct_lb = Text("100%", 9.5, True, T.ON_BG_MED)
        rl.addWidget(self.pct_lb)
        rl.addWidget(PaintWidget(i_battery, 20, 16))
        rl.addSpacing(4)
        self.vsys_lb = Text("4.9 V", 9.0, False, T.ON_BG_LOW)
        self.pir_lb = Text("PIR", 9.0, False, T.ON_BG_LOW)
        for lb in (self.vsys_lb, self.pir_lb):
            lb.setContentsMargins(0, 0, 4, 0)
            rl.addWidget(lb)
        rl.addStretch(1)
        lay.addWidget(row)

        lay.addSpacing(12)
        thumb = QLabel()
        thumb.setStyleSheet("background:transparent;")
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setMinimumHeight(T.THUMB_MIN)
        p = os.path.join(HERE, "device_card.png")
        if os.path.exists(p):
            thumb.setPixmap(QPixmap(p).scaled(QSize(200, 168), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lay.addWidget(thumb, 1)

        foot = QWidget(); foot.setFixedHeight(T.FOOTER_H); foot.setStyleSheet("background:transparent;")
        fl = QHBoxLayout(foot); fl.setContentsMargins(0, 0, -8, 8)
        fl.addStretch(1)
        fl.addWidget(IconButton(i_crosshair, 40))
        lay.addWidget(foot)

    def set_status(self, d):
        v = d.get("vsys") or 0.0
        self.vsys_lb.setText(("%.1f V" % v) if v > 0.5 else "USB")
        self.pir_lb.setText("PIR ●" if d.get("present") else "PIR ○")

    def mousePressEvent(self, e):
        if self.clicked:
            self.clicked()


# ============ top-level pages ============

class DevicesPage(QWidget):
    def __init__(self, on_open=None):
        super().__init__()
        self.card = DeviceCard(self)
        body = QHBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.addStretch(1)
        body.addWidget(self.card)
        body.addStretch(1)
        self.card.clicked = on_open
        self.tg1 = IconButton(i_grid, 44, 32, self)
        self.tg2 = IconButton(i_list, 44, 32, self)

    def update_data(self, d):
        self.card.set_status(d)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.tg2.move(self.width() - 26 - 44, 26)
        self.tg1.move(self.width() - 26 - 44 - 48, 26)


class PageTitle(QWidget):
    def __init__(self, title, sub="", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(Text(title, 17.0, True))
        if sub:
            lay.addWidget(Text(sub, 9.5, False, T.ON_BG_LOW))


class SessionsPage(QWidget):
    ROWS = [
        ("10:42 - 11:07", "00:24:51", "312", "634 dps", "High"),
        ("10:15 - 10:38", "00:22:04", "271", "512 dps", "Medium"),
        ("09:58 - 10:09", "00:11:37", "118", "488 dps", "Medium"),
        ("09:31 - 09:52", "00:20:18", "204", "701 dps", "High"),
        ("09:04 - 09:12", "00:08:40", "86", "356 dps", "Low"),
    ]

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(34, 26, 34, 24)
        lay.setSpacing(16)
        lay.addWidget(PageTitle("Sessions", "Every engagement the infrared sensor recorded"))

        tiles = QHBoxLayout(); tiles.setSpacing(12)
        self.t_sess = StatTile("Sessions today", "-", "decided by the PIR sensor")
        self.t_shots = StatTile("Total shots", "-", "trigger presses")
        self.t_peak = StatTile("Peak rate", "-", "range ±2000 dps")
        self.t_temp = StatTile("Die temperature", "-", "on the MPU-6500")
        for t in (self.t_sess, self.t_shots, self.t_peak, self.t_temp):
            t.setFixedHeight(84)
            tiles.addWidget(t)
        lay.addLayout(tiles)

        # the summary must agree with the log below it, otherwise the page
        # contradicts itself on screen
        n = len(self.ROWS)
        shots = sum(int(r[2]) for r in self.ROWS)
        peak = max(int(r[3].split()[0]) for r in self.ROWS)
        self.t_sess.set_value("%d session%s" % (n, "" if n == 1 else "s"))
        self.t_shots.set_value("%d shots" % shots)
        self.t_peak.set_value("%d dps" % peak)
        self.t_temp.set_value("-")

        card = Card(T.RADIUS_LG, T.SURFACE)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 8, 0, 8)
        cl.setSpacing(0)
        head = QWidget(); hl = QHBoxLayout(head)
        hl.setContentsMargins(20, 6, 20, 10)
        for w, s in ((150, "Start"), (110, "Duration"), (90, "Shots"), (110, "Peak rate"), (0, "Intensity")):
            lb = Text(s, 9.0, False, T.ON_BG_LOW)
            if w:
                lb.setFixedWidth(w)
            hl.addWidget(lb)
        hl.addStretch(1)
        cl.addWidget(head)
        cl.addWidget(Divider())
        for i, (a, b, c, d, e) in enumerate(self.ROWS):
            rw = QWidget(); rl = QHBoxLayout(rw)
            rl.setContentsMargins(20, 10, 20, 10)
            for w, s, bold in ((150, a, False), (110, b, False), (90, c, False), (110, d, False)):
                lb = Text(s, 10.0, bold, T.ON_BG)
                lb.setFixedWidth(w)
                rl.addWidget(lb)
            col = {"High": T.ERROR, "Medium": T.WARN, "Low": T.SUCCESS}[e]
            chip = QLabel(e)
            chip.setAlignment(Qt.AlignCenter)
            chip.setFixedSize(44, 20)
            chip.setFont(app_font(9.0, True))
            chip.setStyleSheet("color:%s;background:%s;border-radius:4px;" % (col, rgba(col, 0.16).name(QColor.HexArgb)))
            rl.addWidget(chip)
            rl.addStretch(1)
            cl.addWidget(rw)
            if i < len(self.ROWS) - 1:
                cl.addWidget(Divider())
        lay.addWidget(card, 1)

    def update_data(self, d):
        self.t_temp.set_value("%.1f °C" % (d.get("temp") or 0))


class CloudPage(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(34, 26, 34, 24)
        lay.setSpacing(16)
        lay.addWidget(PageTitle("Cloud", "ThingSpeak channel · uplink telemetry and downlink commands"))

        tiles = QHBoxLayout(); tiles.setSpacing(12)
        self.t_state = StatTile("Channel", "-", "ThingSpeak")
        self.t_up = StatTile("Records", "-", "rows read from the channel")
        self.t_last = StatTile("Last record", "-", "UTC timestamp")
        self.t_ratio = StatTile("Packing", "15:1", "15 samples packed per field")
        for t in (self.t_state, self.t_up, self.t_last, self.t_ratio):
            t.setFixedHeight(84)
            tiles.addWidget(t)
        lay.addLayout(tiles)

        body = QHBoxLayout(); body.setSpacing(12)

        left = Card(T.RADIUS_LG, T.SURFACE)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(20, 16, 20, 16)
        ll.setSpacing(10)
        ll.addWidget(Text("Field map", 11.0, True))
        for f, name in (("field1", "Yaw rate gz (dps)"), ("field2", "Pitch rate gy (dps)"),
                        ("field3", "Temperature (°C)"), ("field4", "Trigger count"),
                        ("field5", "Operator present (0/1)"), ("field6", "Session length (s)"),
                        ("field7", "Supply voltage (V)"), ("field8", "Packed waveform (base64)")):
            rw = QWidget(); rl = QHBoxLayout(rw)
            rl.setContentsMargins(0, 0, 0, 0)
            k = Text(f, 9.5, True, T.PRIMARY); k.setFixedWidth(58)
            rl.addWidget(k)
            rl.addWidget(Text(name, 9.5, False, T.ON_BG))
            rl.addStretch(1)
            ll.addWidget(rw)
        ll.addStretch(1)
        body.addWidget(left, 1)

        right = Card(T.RADIUS_LG, T.SURFACE)
        rl2 = QVBoxLayout(right)
        rl2.setContentsMargins(20, 16, 20, 16)
        rl2.setSpacing(10)
        rl2.addWidget(Text("Yaw rate history (field 1)", 11.0, True))
        sp = Sparkline(color=T.SECONDARY)
        sp.synth(-62, 9, 6)
        self.sp_rssi = sp
        sp.synth(0, 6, 0.6)
        rl2.addWidget(sp, 1)
        rl2.addWidget(Text("one point per record, oldest on the left", 9.0, False, T.ON_BG_LOW))
        body.addWidget(right, 1)

        lay.addLayout(body, 1)

    def update_data(self, d):
        net = (d.get("net") or "off")
        self.t_state.set_value({"cloud": "connected", "serial": "serial",
                                "mock": "synthetic", "off": "unconfigured"}.get(net, net))
        self.t_up.set_value("%d" % (d.get("rows") or 0))
        at = (d.get("at") or "")
        self.t_last.set_value(at[11:19] if len(at) > 18 else "-")
        self.sp_rssi.push(float(d.get("gz") or 0.0))


class ProtoButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(30)
        self.setFont(app_font(9.5, True))
        self.setStyleSheet(
            "QPushButton{color:%s;background:%s;border:none;border-radius:%dpx;}"
            "QPushButton:hover{background:%s;}"
            "QPushButton:pressed{background:%s;}"
            % (T.ON_BG, T.SURFACE_2, T.RADIUS, T.SURFACE_3, T.PRIMARY))


class ProfilesPage(QWidget):
    DATA = [
        ("Default", "18 c/deg · 0.4 dps dead zone · 35 Hz cutoff", True, "#CFG 2 4 35"),
        ("Precision", "9 c/deg · 0.3 dps dead zone · 25 Hz cutoff", False, "#CFG 1 3 25"),
        ("Flick", "36 c/deg · 0.6 dps dead zone · 45 Hz cutoff", False, "#CFG 3 6 45"),
    ]

    def __init__(self, on_send=None):
        self.on_send = on_send
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(34, 26, 34, 24)
        lay.setSpacing(16)
        lay.addWidget(PageTitle("Profiles", "Local JSON · pushed to the device, mirrored to the cloud"))

        grid = QHBoxLayout(); grid.setSpacing(12)
        for name, desc, active, cmd in self.DATA:
            c = Card(T.RADIUS_LG, T.SURFACE)
            c.setFixedHeight(150)
            cl = QVBoxLayout(c)
            cl.setContentsMargins(18, 16, 18, 14)
            cl.setSpacing(8)
            top = QHBoxLayout(); top.setContentsMargins(0, 0, 0, 0)
            top.addWidget(Text(name, 12.0, True))
            top.addStretch(1)
            if active:
                chip = QLabel("In use")
                chip.setAlignment(Qt.AlignCenter)
                chip.setFixedSize(52, 20)
                chip.setFont(app_font(9.0, True))
                chip.setStyleSheet("color:%s;background:%s;border-radius:4px;"
                                   % (T.PRIMARY, rgba(T.PRIMARY, 0.16).name(QColor.HexArgb)))
                top.addWidget(chip)
            cl.addLayout(top)
            cl.addWidget(Text(desc, 9.5, False, T.ON_BG_MED))
            cl.addStretch(1)
            btn = ProtoButton("Send to device")
            btn.clicked.connect(lambda _=False, c=cmd: self.on_send and self.on_send(c))
            cl.addWidget(btn)
            grid.addWidget(c)
        grid.addStretch(1)
        lay.addLayout(grid)
        lay.addStretch(1)


# ============ device detail ============

class DeviceDetailPage(QWidget):
    def __init__(self, on_back=None):
        super().__init__()
        self.on_back = on_back
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        side = QWidget()
        side.setFixedWidth(T.SIDEBAR_W)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(18, 26, 12, 20)
        sl.setSpacing(2)
        back = QWidget(); bl = QHBoxLayout(back)
        bl.setContentsMargins(0, 0, 0, 14); bl.setSpacing(9)
        bb = IconButton(i_back, 26, 26)
        if on_back:
            bb.clicked.connect(on_back)
        bl.addWidget(bb)
        bl.addWidget(Text("Back to devices", 9.5, False, T.ON_BG_MED))
        bl.addStretch(1)
        sl.addWidget(back)

        self.items = []
        for i, n in enumerate(("Sensitivity", "Assignments", "Lighting", "Device settings", "About")):
            it = SubNavItem(n, active=(i == 0))
            self.items.append(it)
            sl.addWidget(it)
        sl.addStretch(1)
        root.addWidget(side)

        body = QWidget()
        bl2 = QVBoxLayout(body)
        bl2.setContentsMargins(8, 26, 34, 24)
        bl2.setSpacing(14)
        bl2.addWidget(PageTitle("Sensitivity", "DpiPanel · gain, dead zone and filtering"))

        panel = Card(T.RADIUS_LG, T.SURFACE)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(22, 18, 22, 18)
        pl.setSpacing(16)
        pl.addWidget(Text("Gain curve", 11.0, True))
        for lab, lo, hi, v, u in (("Yaw gain (counts / degree)", 3, 60, 18, ""),
                                  ("Pitch gain (counts / degree)", 3, 60, 18, ""),
                                  ("Soft dead zone (dps x 10)", 0, 20, 4, ""),
                                  ("Low-pass cutoff (Hz)", 10, 60, 35, " Hz")):
            pl.addWidget(SliderRow(lab, lo, hi, v, u))
        bl2.addWidget(panel)

        canvas = Card(T.RADIUS_LG, T.SURFACE)
        cl = QVBoxLayout(canvas)
        cl.setContentsMargins(22, 16, 22, 16)
        cl.setSpacing(8)
        cl.addWidget(Text("Live angular rate (DpiCanvas)", 11.0, True))
        sp = Sparkline(color=T.PRIMARY)
        sp.synth(0, 120, 26)
        self.sp_live = sp
        cl.addWidget(sp, 1)
        bl2.addWidget(canvas, 1)
        root.addWidget(body, 1)

    def update_data(self, d):
        self.sp_live.push(float(d.get("gz") or 0.0))


# ============ shell ============

class Header(QWidget):
    def __init__(self, on_nav):
        super().__init__()
        self.setFixedHeight(T.HEADER_H)
        self.setStyleSheet("background:%s;" % T.BG)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(22, 0, 18, 0)
        lay.setSpacing(0)
        lay.addWidget(PaintWidget(i_logo, 40, 40))
        lay.addSpacing(56)
        self.tabs = []
        for i, n in enumerate(("Devices", "Sessions", "Cloud", "Profiles")):
            t = NavTab(n, active=(i == 0))
            t.clicked.connect(on_nav)
            self.tabs.append(t)
            lay.addWidget(t)
            lay.addSpacing(24)
        lay.addStretch(1)

        pill = QFrame()
        pill.setFixedHeight(38)
        pill.setStyleSheet("QFrame{background:%s;border-radius:%dpx;}" % (T.SURFACE, T.RADIUS))
        pl = QHBoxLayout(pill)
        pl.setContentsMargins(12, 0, 16, 0)
        pl.setSpacing(9)
        pl.addWidget(PaintWidget(i_desktop, 26, 26))
        pl.addWidget(Text("Desktop: Default", 10.0))
        lay.addWidget(pill)
        lay.addSpacing(16)
        lay.addWidget(IconButton(i_gear, 34))
        lay.addSpacing(2)
        lay.addWidget(IconButton(i_user, 34))

    def set_active(self, name):
        for t in self.tabs:
            t.set_active(t.name == name)


class StatusBar(QWidget):
    def __init__(self, text):
        super().__init__()
        self.setFixedHeight(T.STATUS_H)
        self.setStyleSheet("background:%s;" % T.STATUSBAR)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.lb = Text(text, 10.0)
        self.lb.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lb)

    def set_text(self, t):
        self.lb.setText(t)


class MainWindow(QWidget):
    def __init__(self, source=None):
        super().__init__()
        self.setWindowTitle("PICO GUN MOUSE Studio")
        self.resize(1030, 768)
        self.setAttribute(Qt.WA_StyledBackground, False)

        self.detail = DeviceDetailPage(on_back=self.close_detail)
        self.stack = QStackedWidget()
        self.pages = {
            "Devices": DevicesPage(on_open=self.open_detail),
            "Sessions": SessionsPage(),
            "Cloud": CloudPage(),
            "Profiles": ProfilesPage(on_send=self.send_profile),
        }
        order = ("Devices", "Sessions", "Cloud", "Profiles")
        for k in order:
            self.stack.addWidget(self.pages[k])

        self.source = source if source is not None else default_source()
        self.header = Header(self.on_nav)
        self.status = StatusBar("source: %s" % self.source.name)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.header)
        self.content = QStackedWidget()
        self.content.addWidget(self.stack)
        self.content.addWidget(self.detail)
        root.addWidget(self.content, 1)
        root.addWidget(self.status)

    def send_profile(self, cmd):
        try:
            res = self.source.send(cmd)
        except Exception as e:
            res = "send failed: %r" % (e,)
        self.status.set_text("%s  →  %s" % (cmd, res))
        self.profile_flash = res

    def _tick(self):
        try:
            d = self.source.poll()
        except Exception as e:
            self.status.set_text("source error: %r" % (e,))
            return
        if not d:
            self.status.set_text("%s  ·  %s" % (self.source.name, self.source.note))
            return
        self.status.set_text(
            "%s  ·  \u0394gz %+.1f dps  \u00b7  %.1f\u00b0C  \u00b7  %d shots  \u00b7  %s"
            % (self.source.name, d.get("gz", 0.0), d.get("temp", 0.0),
               d.get("shots", 0), self.source.note))
        w = self.content.currentWidget()
        if w is self.stack:
            w = self.stack.currentWidget()
        fn = getattr(w, "update_data", None)
        if fn:
            try:
                fn(d)
            except Exception as e:
                self.status.set_text("update_data failed: %r" % (e,))

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(T.BG))
        p.end()

    def on_nav(self, name):
        self.header.set_active(name)
        self.content.setCurrentIndex(0)
        self.stack.setCurrentWidget(self.pages[name])

    def open_detail(self):
        self.header.set_active("Devices")
        self.content.setCurrentWidget(self.detail)

    def close_detail(self):
        self.content.setCurrentIndex(0)

    def show_page(self, name):
        self.on_nav(name)


def main():
    qa = QApplication(sys.argv)
    w = MainWindow(); w.show()
    qa.exec_()


if __name__ == "__main__":
    main()