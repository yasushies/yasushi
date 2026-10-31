"""Instagram投稿用の画像（JPEG）を作る。

写真は切らずに縮小して収め、文字と院名を入れる。写真がなければ文字だけで作る。

使い方:
    # ストーリー（1080x1920）
    python3 make_post_images.py story --out story.jpg [--photo p.jpg] [--text-file t.txt]
    # フィード画像1枚（1080x1350）
    python3 make_post_images.py feed --out feed.jpg [--photo p.jpg] [--text-file t.txt]
    # カルーセル（1080x1350 を複数枚）
    python3 make_post_images.py carousel --outdir slides/ --slides-file s.txt [--photos p1.jpg p2.jpg ...]

テキストファイルの改行はそのまま改行になる。
カルーセルのスライド文字は「---」だけの行で区切る。各スライドの1行目が見出し、残りが本文。
写真は先頭のスライドから順に1枚ずつ使い、足りないスライドは文字だけになる。
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:  # iPhoneのHEIC写真も読めるようにする（pillow-heif があれば）
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

BG = (244, 239, 231)        # 生成り
INK = (61, 90, 71)          # 深い緑（院の掛け軸の色に合わせる）
BODY = (70, 70, 64)
SUB = (120, 130, 120)
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_INDEX_JP = 0           # .ttc 内の日本語（JP）フェイス
FOOTER = "整体院 心和｜所沢"

STORY = dict(w=1080, h=1920, top=250, bottom=1920 - 250, text_max_h=520)
FEED = dict(w=1080, h=1350, top=90, bottom=1350 - 70, text_max_h=380)
MARGIN_X = 90
PHOTO_MARGIN_X = 60
GAP = 56
FOOTER_SIZE = 34
FOOTER_H = 60


def font(path, size):
    return ImageFont.truetype(path, size, index=FONT_INDEX_JP)


# 行頭に来てはいけない文字（句読点や閉じかっこ）
NO_LINE_START = "、。，．,.!?！？)）」』】〕〉》ー～ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ"


def wrap(draw, text, fnt, max_w):
    """日本語は1文字ずつ折り返す。手で入れた改行は尊重する。"""
    lines = []
    for para in text.split("\n"):
        line = ""
        for ch in para:
            if (draw.textlength(line + ch, font=fnt) > max_w and line
                    and ch not in NO_LINE_START):
                lines.append(line)
                line = ch
            else:
                line += ch
        lines.append(line)
    return lines


def fit_text(draw, text, path, max_w, max_h, sizes):
    """枠に収まる一番大きい文字サイズで折り返した行を返す。

    手で入れた改行だけで収まるサイズがあればそれを優先し、
    「した」だけが次の行に落ちるような折り返しを避ける。
    """
    paras = text.split("\n")
    for size in sizes:
        fnt = font(path, size)
        line_h = int(size * 1.45)
        if (all(draw.textlength(p, font=fnt) <= max_w for p in paras)
                and len(paras) * line_h <= max_h):
            return fnt, paras, line_h
    for size in sizes:
        fnt = font(path, size)
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


def draw_lines(draw, lines, fnt, line_h, y, w, fill, align="center", x0=MARGIN_X):
    for line in lines:
        x = (w - draw.textlength(line, font=fnt)) / 2 if align == "center" else x0
        draw.text((x, y), line, font=fnt, fill=fill)
        y += line_h
    return y


def draw_footer(draw, y, w):
    fnt = font(FONT_REG, FOOTER_SIZE)
    draw.text(((w - draw.textlength(FOOTER, font=fnt)) / 2, y), FOOTER, font=fnt, fill=SUB)


def photo_card(fmt, photo_path, text, dst):
    """写真（任意）と見出し文字（任意）を縦に並べたカード。"""
    w, h = fmt["w"], fmt["h"]
    canvas = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(canvas)
    text = (text or "").strip()

    if not photo_path:
        # 文字だけ：大きめの文字を中央に置く
        if not text:
            sys.exit("写真も文字もありません")
        fnt, lines, line_h = fit_text(draw, text, FONT_BOLD, w - 2 * MARGIN_X,
                                      fmt["bottom"] - fmt["top"] - FOOTER_H - GAP * 2,
                                      range(96, 43, -4))
        block = len(lines) * line_h
        y = fmt["top"] + (fmt["bottom"] - fmt["top"] - FOOTER_H - GAP - block) // 2
        y = draw_lines(draw, lines, fnt, line_h, y, w, INK)
        bar_y = y + GAP // 2
        draw.line(((w / 2 - 40, bar_y), (w / 2 + 40, bar_y)), fill=INK, width=4)
        draw_footer(draw, fmt["bottom"] - FOOTER_H, w)
        canvas.save(dst, "JPEG", quality=90)
        return

    photo = ImageOps.exif_transpose(Image.open(photo_path)).convert("RGB")
    if text:
        fnt, lines, line_h = fit_text(draw, text, FONT_BOLD, w - 2 * MARGIN_X,
                                      fmt["text_max_h"], range(84, 39, -4))
    else:
        fnt, lines, line_h = None, [], 0
    text_h = len(lines) * line_h

    # 写真は残りの高さに収まるように縮小（切り抜かない）
    avail_h = fmt["bottom"] - fmt["top"] - text_h - FOOTER_H - (GAP * 2 if text else GAP)
    scale = min((w - 2 * PHOTO_MARGIN_X) / photo.width, avail_h / photo.height)
    photo = photo.resize((int(photo.width * scale), int(photo.height * scale)), Image.LANCZOS)
    photo = rounded(photo, 28)

    total = text_h + (GAP if text else 0) + photo.height + GAP + FOOTER_H
    y = fmt["top"] + (fmt["bottom"] - fmt["top"] - total) // 2
    y = draw_lines(draw, lines, fnt, line_h, y, w, INK)
    if text:
        y += GAP
    canvas.paste(photo, ((w - photo.width) // 2, y))
    draw_footer(draw, y + photo.height + GAP, w)
    canvas.save(dst, "JPEG", quality=90)


def text_slide(heading, body, page, total, dst):
    """カルーセルの説明スライド：見出しと本文、右上にページ番号。"""
    w, h = FEED["w"], FEED["h"]
    canvas = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(canvas)

    num = font(FONT_REG, 34)
    label = f"{page}/{total}"
    draw.text((w - MARGIN_X - draw.textlength(label, font=num), 70), label, font=num, fill=SUB)

    max_w = w - 2 * MARGIN_X
    hf, hlines, hline_h = fit_text(draw, heading, FONT_BOLD, max_w, 300, range(72, 39, -4))
    bf, blines, bline_h = (fit_text(draw, body, FONT_REG, max_w, 640, range(46, 29, -2))
                           if body else (None, [], 0))
    block = len(hlines) * hline_h + (GAP + len(blines) * bline_h if body else 0)
    y = 160 + (h - 160 - 70 - FOOTER_H - block) // 2
    y = draw_lines(draw, hlines, hf, hline_h, y, w, INK, align="left")
    if body:
        draw.line(((MARGIN_X, y + GAP // 2 - 8), (MARGIN_X + 80, y + GAP // 2 - 8)), fill=INK, width=4)
        y += GAP
        draw_lines(draw, blines, bf, bline_h, y, w, BODY, align="left")
    draw_footer(draw, h - 70 - FOOTER_H, w)
    canvas.save(dst, "JPEG", quality=90)


def carousel(slides_text, photos, outdir):
    slides = [s.strip() for s in slides_text.replace("\r\n", "\n").split("\n---\n")]
    slides = [s for s in slides if s]
    if not 2 <= len(slides) <= 10:
        sys.exit(f"スライドは2〜10枚にしてください（今は{len(slides)}枚）")
    os.makedirs(outdir, exist_ok=True)
    for i, slide in enumerate(slides):
        heading, _, body = slide.partition("\n")
        dst = os.path.join(outdir, f"slide_{i + 1:02d}.jpg")
        photo = photos[i] if i < len(photos) else None
        if photo:
            # 写真のあるスライドは文字を写真の上にまとめて置く
            photo_card(FEED, photo, slide, dst)
        elif i == 0:
            photo_card(FEED, None, slide, dst)
        else:
            text_slide(heading, body.strip(), i + 1, len(slides), dst)
        print(dst)


def read(path):
    if not path:
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="kind", required=True)
    for kind in ("story", "feed"):
        s = sub.add_parser(kind)
        s.add_argument("--out", required=True)
        s.add_argument("--photo")
        s.add_argument("--text-file")
    c = sub.add_parser("carousel")
    c.add_argument("--outdir", required=True)
    c.add_argument("--slides-file", required=True)
    c.add_argument("--photos", nargs="*", default=[])
    a = p.parse_args()

    if a.kind == "carousel":
        carousel(read(a.slides_file), a.photos, a.outdir)
    else:
        photo_card(STORY if a.kind == "story" else FEED, a.photo, read(a.text_file), a.out)
        print(a.out)


if __name__ == "__main__":
    main()
