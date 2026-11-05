"""Generate realistic-looking bank/receipt mock images for demo data."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont


FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\tahoma.ttf"),
    Path(r"C:\Windows\Fonts\segoeui.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
]


def fa(text: str) -> str:
    """Shape + bidi-reorder Persian/Arabic text for correct Pillow rendering."""
    if not text:
        return ""
    return get_display(arabic_reshaper.reshape(str(text)))


def _font(size: int) -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _text_w(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def make_bank_receipt(
    *,
    amount: int,
    payer_name: str,
    unit_number: str,
    title: str = "رسید پرداخت شارژ ساختمان",
    status_label: str = "موفق",
    ref_code: str = "BH-240110-88421",
    bank_name: str = "بانک نمونه BuildingHub",
) -> ContentFile:
    width, height = 720, 1000
    img = Image.new("RGB", (width, height), "#eef6f4")
    draw = ImageDraw.Draw(img)

    # header
    draw.rectangle((0, 0, width, 160), fill="#0f766e")
    draw.rectangle((0, 160, width, 168), fill="#2dd4bf")

    font_xl = _font(28)
    font_lg = _font(22)
    font_md = _font(18)
    font_sm = _font(15)
    font_xs = _font(13)

    def center(y: int, text: str, font, fill="#ffffff"):
        shaped = fa(text)
        w = _text_w(draw, shaped, font)
        draw.text(((width - w) / 2, y), shaped, font=font, fill=fill)

    center(30, bank_name, font_xl)
    center(78, "رسید انتقال وجه / پرداخت شارژ", font_md, "#ccfbf1")
    center(118, status_label, font_sm, "#ecfdf5")

    # white card
    draw.rounded_rectangle((40, 200, width - 40, height - 80), radius=24, fill="#ffffff", outline="#c7e6e0", width=2)

    rows = [
        ("عنوان", title),
        ("پرداخت‌کننده", payer_name),
        ("واحد", str(unit_number)),
        ("مبلغ (تومان)", f"{amount:,}"),
        ("شماره پیگیری", ref_code),
        ("تاریخ", "۱۴۰۴/۰۸/۱۴ - ۱۴:۳۲"),
        ("مبدا", "کارت **** ۱۲۳۴"),
        ("مقصد", "حساب ساختمان / مدیر"),
        ("توضیح", "پرداخت سهم شارژ ماهانه"),
    ]

    y = 230
    left = 70
    right = width - 70
    for label, value in rows:
        label_s = fa(label)
        value_s = fa(value)
        draw.text((left, y), label_s, font=font_sm, fill="#64748b")
        vw = _text_w(draw, value_s, font_md)
        draw.text((right - vw, y - 1), value_s, font=font_md, fill="#0f172a")
        y += 56
        draw.line((left, y - 18, right, y - 18), fill="#e2e8f0", width=1)

    # circular stamp
    stamp = (width - 250, height - 290, width - 90, height - 130)
    draw.ellipse(stamp, outline="#0f766e", width=4)
    stamp_font = _font(17)
    cx = (stamp[0] + stamp[2]) / 2
    for i, line in enumerate(["تأیید شد", "پرداخت شده"]):
        shaped = fa(line)
        tw = _text_w(draw, shaped, stamp_font)
        draw.text((cx - tw / 2, stamp[1] + 42 + i * 28), shaped, font=stamp_font, fill="#0f766e")

    # amount highlight chip
    chip = fa(f"مبلغ قابل پرداخت: {amount:,} تومان")
    chip_font = _font(16)
    cw = _text_w(draw, chip, chip_font)
    chip_x = (width - cw) / 2 - 18
    chip_y = height - 330
    draw.rounded_rectangle((chip_x, chip_y, chip_x + cw + 36, chip_y + 40), radius=12, fill="#ecfdf5", outline="#99f6e4")
    draw.text((chip_x + 18, chip_y + 10), chip, font=chip_font, fill="#0f766e")

    # footer
    draw.rectangle((0, height - 58, width, height), fill="#0b3d3a")
    center(height - 40, "BuildingHub Demo Receipt — فقط برای محیط آزمایشی", font_xs, "#99f6e4")

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return ContentFile(buf.getvalue(), name=f"receipt-{ref_code}.png")


def make_maintenance_photo(*, label: str = "خرابی گزارش‌شده") -> ContentFile:
    width, height = 960, 680
    img = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(img)

    # faux photo backdrop
    for i in range(14):
        shade = 28 + i * 7
        draw.rectangle((0, i * 50, width, (i + 1) * 50), fill=(shade, shade + 12, shade + 22))

    draw.rounded_rectangle((50, 60, width - 50, height - 60), radius=30, fill="#111827", outline="#334155", width=3)

    font_lg = _font(32)
    font_md = _font(22)
    font_sm = _font(16)

    def center(y, text, font, fill="#e2e8f0"):
        shaped = fa(text)
        w = _text_w(draw, shaped, font)
        draw.text(((width - w) / 2, y), shaped, font=font, fill=fill)

    center(190, "تصویر پیوست درخواست تعمیر", font_lg, "#f8fafc")
    center(270, label, font_md, "#5eead4")
    center(340, "نمونه واقعی‌شکل برای دمو BuildingHub", font_sm, "#94a3b8")

    for x, y in [(80, 90), (width - 130, 90), (80, height - 140), (width - 130, height - 140)]:
        draw.rectangle((x, y, x + 50, y + 8), fill="#14b8a6")
        draw.rectangle((x, y, x + 8, y + 50), fill="#14b8a6")

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return ContentFile(buf.getvalue(), name="maintenance-demo.png")
