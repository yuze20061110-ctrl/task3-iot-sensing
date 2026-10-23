# -*- coding: utf-8 -*-
"""Interface language for the desktop client.

Every user-visible string is written in English in the source and pulled through
L() at render time.  Language choice is stored in settings.json next to this file
so it survives a restart.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "settings.json")

LANGS = [("en", "English"), ("zh", "中文")]

ZH = {
    # ---- navigation ----
    "Devices": "设备",
    "Sessions": "使用记录",
    "Cloud": "云端",
    "Profiles": "配置",
    "Desktop: Default": "桌面：默认",
    # ---- sessions ----
    "Every engagement the infrared sensor recorded": "红外传感器记录的每一次使用",
    "Sessions today": "今日使用次数",
    "decided by the PIR sensor": "由红外传感器判定",
    "Total shots": "总扳机次数",
    "trigger presses": "扳机触发次数",
    "Peak rate": "峰值速率",
    "range ±2000 dps": "量程 ±2000 dps",
    "Die temperature": "芯片温度",
    "on the MPU-6050": "来自 MPU-6050",
    "Start": "开始时间",
    "Duration": "持续时长",
    "Shots": "次数",
    "Intensity": "强度",
    "High": "高",
    "Medium": "中",
    "Low": "低",
    # ---- cloud ----
    "ThingSpeak channel · uplink telemetry and downlink commands":
        "ThingSpeak 通道 · 上行遥测与下行指令",
    "Channel": "通道",
    "Records": "记录数",
    "rows read from the channel": "从通道读取的行数",
    "Last record": "最新记录",
    "UTC timestamp": "UTC 时间戳",
    "Packing": "打包",
    "15 samples packed per field": "每字段打包 15 个采样",
    "Field map": "字段映射",
    "Yaw rate gz (dps)": "偏航角速度 gz (dps)",
    "Pitch rate gy (dps)": "俯仰角速度 gy (dps)",
    "Temperature (°C)": "温度 (°C)",
    "Trigger count": "扳机计数",
    "Operator present (0/1)": "使用者存在 (0/1)",
    "Session length (s)": "单次时长 (s)",
    "Supply voltage (V)": "供电电压 (V)",
    "Packed waveform (base64)": "打包波形 (base64)",
    "Yaw rate history (field 1)": "偏航角速度历史 (字段 1)",
    "one point per record, oldest on the left": "每条记录一个点，最左为最早",
    # ---- profiles ----
    "Default": "默认",
    "Precision": "精准",
    "Flick": "甩枪",
    "18 c/deg · 0.4 dps dead zone · 35 Hz cutoff": "18 计数/度 · 0.4 dps 死区 · 35 Hz 截止",
    "9 c/deg · 0.3 dps dead zone · 25 Hz cutoff": "9 计数/度 · 0.3 dps 死区 · 25 Hz 截止",
    "36 c/deg · 0.6 dps dead zone · 45 Hz cutoff": "36 计数/度 · 0.6 dps 死区 · 45 Hz 截止",
    "In use": "使用中",
    "No usage recorded yet": "尚未记录到使用",
    "The log fills as the infrared sensor sees you.": "红外传感器检测到使用者后会自动记录。",
    "Sensitivity (counts / degree)": "灵敏度（计数 / 度）",
    "Push to device": "下发到设备",
    "Local JSON · pushed to the device, mirrored to the cloud": "本地存储 · 可下发到设备，并同步到云端",
    "Send to device": "下发到设备",
    # ---- detail page ----
    "Back to devices": "返回设备",
    "Sensitivity": "灵敏度",
    "Assignments": "分配",
    "Lighting": "灯光",
    "Device settings": "设备设置",
    "About": "关于",
    "DpiPanel · gain, dead zone and filtering": "灵敏度面板 · 增益、死区与滤波",
    "Gain curve": "增益曲线",
    "Yaw gain (counts / degree)": "偏航增益 (计数/度)",
    "Pitch gain (counts / degree)": "俯仰增益 (计数/度)",
    "Soft dead zone (dps x 10)": "软死区 (dps × 10)",
    "Low-pass cutoff (Hz)": "低通截止 (Hz)",
    "Live angular rate (DpiCanvas)": "实时角速度",
    # ---- device card ----
    "PIR": "红外",
    "PIR ●": "红外 ●",
    "PIR ○": "红外 ○",
    "USB": "USB",
    "PICO GUN MOUSE Studio": "PICO GUN MOUSE Studio",
    # ---- status bar ----
    "source: %s": "数据源: %s",
    "send failed: %r": "下发失败: %r",
    "source error: %r": "数据源错误: %r",
    "source error: %s": "数据源错误: %s",
    "update_data failed: %r": "刷新数据失败: %r",
    # ---- settings ----
    "Settings": "设置",
    "Language": "语言",
    "Interface language": "界面语言",
    "Apply": "应用",
    "Cancel": "取消",
    "Language changed. The window reloads.": "语言已切换，窗口将重新载入。",
}

_lang = "en"


def load():
    global _lang
    try:
        with open(SETTINGS, "r", encoding="utf-8") as f:
            v = json.load(f).get("lang", "en")
        if v in ("en", "zh"):
            _lang = v
    except Exception:
        pass
    return _lang


def save():
    try:
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump({"lang": _lang}, f)
    except Exception:
        pass


def current():
    return _lang


def set_lang(code):
    global _lang
    if code in ("en", "zh"):
        _lang = code
        save()


def L(s):
    """Translate one string; unknown strings pass through unchanged."""
    if _lang == "en":
        return s
    return ZH.get(s, s)