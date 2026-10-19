import math, os
from PyQt5.QtCore import Qt, QRectF, QPointF, QSize, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QPixmap, QPainterPath
from PyQt5.QtWidgets import QWidget, QLabel, QFrame, QPushButton, QHBoxLayout, QVBoxLayout, QSlider

import tokens as T

HERE = os.path.dirname(os.path.abspath(__file__))


def rgba(hexs, a=None):
    # Qt reads 8-digit hex as #AARRGGBB, so #RRGGBBAA must be parsed by hand.
    s = hexs.lstrip("#")
    if len(s) == 8:
        c = QColor(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        c.setAlpha(int(s[6:8], 16))
    else:
        c = QColor(hexs)
    if a is not None:
        c.setAlphaF(a)
    return c


def qss(hexs, a=None):
    # stylesheet-safe colour string (#AARRGGBB), which Qt's parser does honour
    return rgba(hexs, a).name(QColor.HexArgb)


def app_font(pt, bold=False, spacing=0.0):
    f = QFont()
    f.setFamilies([T.FONT_EN, T.FONT_CN])
    f.setPointSizeF(pt)
    f.setBold(bold)
    if spacing:
        f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f


# ---------------- icons ----------------

def i_gear(p, r):
    p.setPen(QPen(rgba(T.NAV_IDLE), 1.5)); p.setBrush(Qt.NoBrush)
    cx, cy = r.center().x(), r.center().y()
    rad = min(r.width(), r.height()) / 2 * 0.56
    for i in range(8):
        a = i * math.pi / 4
        p.drawLine(QPointF(cx + math.cos(a) * rad * 1.40, cy + math.sin(a) * rad * 1.40),
                   QPointF(cx + math.cos(a) * rad * 1.00, cy + math.sin(a) * rad * 1.00))
    p.drawEllipse(QPointF(cx, cy), rad, rad)
    p.drawEllipse(QPointF(cx, cy), rad * 0.34, rad * 0.34)


def i_user(p, r):
    p.setPen(QPen(rgba(T.NAV_IDLE), 1.5)); p.setBrush(Qt.NoBrush)
    cx, cy = r.center().x(), r.center().y()
    rad = min(r.width(), r.height()) / 2 * 0.54
    p.drawEllipse(QPointF(cx, cy - rad * 0.44), rad * 0.48, rad * 0.48)
    p.drawArc(QRectF(cx - rad * 0.90, cy - rad * 0.06, rad * 1.80, rad * 1.50), 0, 180 * 16)


def i_desktop(p, r):
    p.setPen(QPen(rgba(T.ON_BG), 1.4)); p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(r.x() + 3, r.y() + 9, 19, 13), 2, 2)
    p.drawLine(QPointF(r.x() + 8, r.y() + 14), QPointF(r.x() + 17, r.y() + 14))


def i_grid(p, r):
    p.setPen(QPen(rgba(T.ON_BG_MED), 1.4)); p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(r.x() + 4, r.y() + 4, r.width() - 8, r.height() - 8), 8, 8)
    p.setBrush(QBrush(rgba(T.ON_BG_MED)))
    for i in range(3):
        p.drawEllipse(QPointF(r.x() + 8.5 + i * 6.5, r.center().y()), 1.5, 1.5)


def i_list(p, r):
    p.setPen(QPen(rgba(T.ON_BG_MED), 1.4)); p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(r.x() + 4, r.y() + 4, r.width() - 8, r.height() - 8), 8, 8)
    p.setBrush(QBrush(rgba(T.ON_BG_MED)))
    for i in range(2):
        p.drawRoundedRect(QRectF(r.x() + 9, r.y() + 9 + i * 6, 12, 2.2), 1, 1)


def i_crosshair(p, r):
    p.setPen(QPen(rgba(T.ON_BG), 1.4)); p.setBrush(Qt.NoBrush)
    cx, cy = r.center().x(), r.center().y()
    rad = min(r.width(), r.height()) / 2 * 0.42
    p.drawEllipse(QPointF(cx, cy), rad, rad)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        p.drawLine(QPointF(cx + dx * rad * 0.30, cy + dy * rad * 0.30),
                   QPointF(cx + dx * rad * 1.55, cy + dy * rad * 1.55))


def i_logo(p, r):
    """Product mark: a bold capital P, drawn as two strokes so it stays crisp at
    any size and needs no font."""
    pen = QPen(rgba(T.ON_BG), max(2.5, r.width() * 0.11), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    cx, cy = r.center().x(), r.center().y()
    h = r.height() * 0.62
    w = r.width() * 0.44
    x0 = cx - w * 0.55
    y0 = cy - h / 2.0
    y1 = cy + h / 2.0
    # stem
    p.drawLine(QPointF(x0, y0), QPointF(x0, y1))
    # bowl
    path = QPainterPath()
    path.moveTo(x0, y0)
    path.lineTo(x0 + w * 0.55, y0)
    path.arcTo(QRectF(x0, y0, w, h * 0.56), 90, -180)
    path.lineTo(x0, y0 + h * 0.56)
    p.drawPath(path)


def i_back(p, r):
    p.setPen(QPen(rgba(T.ON_BG), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.setBrush(Qt.NoBrush)
    cx, cy = r.center().x(), r.center().y()
    p.drawLine(QPointF(cx + 5, cy - 7), QPointF(cx - 4, cy))
    p.drawLine(QPointF(cx - 4, cy), QPointF(cx + 5, cy + 7))


def i_battery(p, r):
    x, y = r.x() + 1, r.y() + r.height() * 0.24
    w, h = r.width() * 0.76, r.height() * 0.50
    p.setPen(QPen(rgba(T.SUCCESS), 1.2)); p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(x, y, w, h), 1.5, 1.5)
    p.setPen(Qt.NoPen); p.setBrush(QBrush(rgba(T.SUCCESS)))
    p.drawRect(QRectF(x + w + 1.2, y + h * 0.28, 1.8, h * 0.44))
    p.drawRect(QRectF(x + 1.6, y + 1.6, w - 3.2, h - 3.2))


# ---------------- primitives ----------------

class PaintWidget(QWidget):
    def __init__(self, fn, w=None, h=None, parent=None):
        super().__init__(parent)
        self._fn = fn
        if w and h:
            self.setFixedSize(w, h)
        elif w:
            self.setFixedWidth(w)
        elif h:
            self.setFixedHeight(h)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        self._fn(p, QRectF(0, 0, self.width(), self.height()))
        p.end()


class IconButton(QPushButton):
    def __init__(self, fn, w=32, h=None, parent=None):
        super().__init__(parent)
        self._fn = fn
        self.setFixedSize(w, h or w)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QPushButton{background:transparent;border:none;border-radius:%dpx;}"
                           "QPushButton:hover{background:rgba(255,255,255,0.07);}" % T.RADIUS)

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        self._fn(p, QRectF(0, 0, self.width(), self.height()))
        p.end()


class Text(QLabel):
    def __init__(self, s, pt=10.0, bold=False, color=None, parent=None):
        super().__init__(s, parent)
        self.setFont(app_font(pt, bold))
        self.setStyleSheet("background:transparent;color:%s;" % (color or T.ON_BG))


class Card(QFrame):
    def __init__(self, radius=T.RADIUS_LG, bg=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame{background:%s;border-radius:%dpx;}"
                           % (bg or T.SURFACE, radius))


class NavTab(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, name, active=False, parent=None):
        super().__init__(parent)
        self.name = name
        self.active = active
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(app_font(10.5))
        fm = QFontMetrics(app_font(10.5))
        self.setFixedSize(fm.horizontalAdvance(name) + 6, T.HEADER_H)

    def set_active(self, v):
        self.active = v
        self.update()

    def mousePressEvent(self, e):
        self.clicked.emit(self.name)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setFont(self.font())
        col = T.PRIMARY if self.active else T.NAV_IDLE
        p.setPen(QPen(QColor(col)))
        p.drawText(self.rect(), Qt.AlignCenter, self.name)
        if self.active:
            fm = QFontMetrics(self.font())
            w = fm.horizontalAdvance(self.name) + 4
            x = (self.width() - w) / 2
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(T.PRIMARY)))
            p.drawRoundedRect(QRectF(x, self.height() - 12, w, 2), 1, 1)
        p.end()


class SubNavItem(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, name, active=False, parent=None):
        super().__init__(parent)
        self.name = name
        self.active = active
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(app_font(10.5))
        self.setFixedHeight(38)

    def set_active(self, v):
        self.active = v
        self.update()

    def mousePressEvent(self, e):
        self.clicked.emit(self.name)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        if self.active:
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(rgba(T.ON_BG, 0.06)))
            p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 6, 6)
            p.setBrush(QBrush(QColor(T.PRIMARY)))
            p.drawRoundedRect(QRectF(0, 10, 2.5, self.height() - 20), 1.2, 1.2)
        p.setFont(self.font())
        p.setPen(QPen(QColor(T.ON_BG if self.active else T.NAV_IDLE)))
        p.drawText(QRectF(14, 0, self.width() - 20, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.name)
        p.end()


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet("background:%s;" % qss(T.OUTLINE))


class SliderRow(QWidget):
    def __init__(self, label, lo, hi, val, unit="", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.addWidget(Text(label, 10.5, False, T.ON_BG))
        self.setStyleSheet("background:transparent;")
        head.addStretch(1)
        self.value = Text("%s%s" % (val, unit), 10.5, True, T.ON_BG)
        head.addWidget(self.value)
        lay.addLayout(head)
        self.s = QSlider(Qt.Horizontal)
        self.s.setRange(lo, hi)
        self.s.setValue(val)
        self.unit = unit
        self.s.setStyleSheet("""
            QSlider::groove:horizontal{height:4px;background:%s;border-radius:2px;}
            QSlider::sub-page:horizontal{height:4px;background:%s;border-radius:2px;}
            QSlider::handle:horizontal{width:14px;height:14px;margin:-5px 0;border-radius:7px;background:#fff;}
        """ % (qss(T.OUTLINE_HI), T.PRIMARY))
        self.s.valueChanged.connect(lambda v: self.value.setText("%d%s" % (v, self.unit)))
        lay.addWidget(self.s)


class Sparkline(QWidget):
    def __init__(self, n=140, color=None, parent=None):
        super().__init__(parent)
        self.n = n
        self.color = color or T.PRIMARY
        self.data = []
        self.setMinimumHeight(120)
        self._seed = 7

    def push(self, v):
        self.data.append(v)
        if len(self.data) > self.n:
            self.data.pop(0)
        self.update()

    def synth(self, base, amp, noise, phase=0.0):
        self.data = []
        x = 0.0
        for i in range(self.n):
            x += 0.23
            v = base + amp * (math.sin(x + phase) * 0.6 + math.sin(x * 2.7 + phase) * 0.4) \
                + noise * (((i * 9301 + 49297) % 233280) / 233280.0 - 0.5)
            self.data.append(v)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(0, 0, self.width(), self.height())
        p.setPen(Qt.NoPen); p.setBrush(QBrush(rgba(T.BG)))
        p.drawRoundedRect(r, 6, 6)
        if len(self.data) < 2:
            p.end(); return
        p.setPen(QPen(rgba(T.OUTLINE), 1))
        for i in range(1, 4):
            y = r.height() * i / 4.0
            p.drawLine(QPointF(0, y), QPointF(r.width(), y))
        lo, hi = min(self.data), max(self.data)
        rng = (hi - lo) or 1.0
        path = QPainterPath()
        for i, v in enumerate(self.data):
            x = r.width() * i / (len(self.data) - 1)
            y = r.height() - (v - lo) / rng * (r.height() * 0.84) - r.height() * 0.08
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        p.setPen(QPen(QColor(self.color), 1.8))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        p.end()


class StatTile(Card):
    def __init__(self, label, value, sub="", parent=None):
        super().__init__(T.RADIUS, T.SURFACE, parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)
        lay.addWidget(Text(label, 9.0, False, T.ON_BG_LOW))
        self.v = Text(value, 18.0, True, T.ON_BG)
        self.v.setWordWrap(False)
        lay.addWidget(self.v)
        if sub:
            self.sub = Text(sub, 8.5, False, T.ON_BG_LOW)
            lay.addWidget(self.sub)
        else:
            self.sub = None

    def set_value(self, value, sub=None):
        self.v.setText(str(value))
        if sub is not None and self.sub is not None:
            self.sub.setText(str(sub))