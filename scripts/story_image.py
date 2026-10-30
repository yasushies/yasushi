"""Instagramストーリー用の画像（1080x1920 JPEG）を作る。

写真は切らずに縮小して中央に置き、上に文字、下に院名を入れる。

使い方:
    python3 story_image.py 入力画像 出力.jpg "画像に入れる文字"
文字の中の改行（\n）はそのまま改行になる。
"""
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1080, 1920
BG = (244, 239, 231)        # 生成り
INK = (61, 90, 71)          # 深い緑（院の掛け軸の色に合わせる）
SUB = (120, 130, 120)
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_INDEX_JP = 0           # .ttc 内の日本語（JP）フェイス
FOOTER = "整体院 心和｜所沢"

# Instagramの上下のUI（アイコンや返信欄）に隠れない範囲
SAFE_TOP, SAFE_BOTTOM = 250, H - 250
MARGIN_X = 90
PHOTO_MAX_W = W - 2 * 60
GAP = 60


def font(path, size):
    return ImageFont.truetype(path, size, index=FONT_INDEX_JP)


def wrap(draw, text, fnt, max_w):
    """日本語は1文字ずつ折り返す。手で入れた改行は尊重する。"""
    lines = []
    for para in text.split("\n"):
        line = ""
        for ch in para:
            if draw.textlength(line + ch, font=fnt) > max_w and line:
                lines.append(line)
                line = ch
            else:
                line += ch
        lines.append(line)
    return lines


def text_block(draw, text, max_w, max_h):
    """枠に収まる一番大きい文字サイズで折り返した行を返す。

    手で入れた改行だけで収まるサイズがあればそれを優先し、
    「した」だけが次の行に落ちるような折り返しを避ける。
    """
    paras = text.split("\n")
    for size in range(84, 47, -4):
        fnt = font(FONT_BOLD, size)
        line_h = int(size * 1.45)
        if (all(draw.textlength(p, font=fnt) <= max_w for p in paras)
                and len(paras) * line_h <= max_h):
            return fnt, paras, line_h
    for size in range(84, 39, -4):
        fnt = font(FONT_BOLD, size)
        lines = wrap(draw, text, fnt, max_w)
        line_h = int(size * 1.45)
        if len(lines) * line_h <= max_h:
            return fnt, lines, line_h
    return fnt, lines, line_h


def rounded(img, radius):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *img.size), radius, fill=255)
    out = Image.new("RGB", img.size, BG)
    out.paste(img, (0, 0), mask)
    return out


def main(src, dst, text):
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)

    photo = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    footer_font = font(FONT_REG, 34)
    footer_h = 60

    text = text.strip()
    text_max_h = 520 if text else 0
    fnt, lines, line_h = text_block(draw, text, W - 2 * MARGIN_X, text_max_h) if text else (None, [], 0)
    text_h = len(lines) * line_h

    # 写真は残りの高さに収まるように縮小（切り抜かない）
    avail_h = SAFE_BOTTOM - SAFE_TOP - text_h - footer_h - (GAP * 2 if text else GAP)
    scale = min(PHOTO_MAX_W / photo.width, avail_h / photo.height)
    photo = photo.resize((int(photo.width * scale), int(photo.height * scale)), Image.LANCZOS)
    photo = rounded(photo, 28)

    total = text_h + (GAP if text else 0) + photo.height + GAP + footer_h
    y = SAFE_TOP + (SAFE_BOTTOM - SAFE_TOP - total) // 2

    for line in lines:
        w = draw.textlength(line, font=fnt)
        draw.text(((W - w) / 2, y), line, font=fnt, fill=INK)
        y += line_h
    if text:
        y += GAP

    canvas.paste(photo, ((W - photo.width) // 2, y))
    y += photo.height + GAP

    w = draw.textlength(FOOTER, font=footer_font)
    draw.text(((W - w) / 2, y), FOOTER, font=footer_font, fill=SUB)

    canvas.save(dst, "JPEG", quality=90)


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3].replace("\\n", "\n") if len(sys.argv) == 4 else "")
