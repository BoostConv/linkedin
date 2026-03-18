"""Carousel PDF generator for LinkedIn posts.

Generates branded PDF carousels using ReportLab with Boost Conversion's
visual identity. Each slide = 1 idea, optimized for LinkedIn's document viewer.
"""
import io
import json
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle


# LinkedIn carousel optimal size (1080x1080px = square, but PDF uses points)
SLIDE_WIDTH = 270 * mm  # ~1080px at 72dpi equivalent
SLIDE_HEIGHT = 270 * mm


@dataclass
class BrandConfig:
    """Brand identity — Charte Graphique Boost Conversion.

    Couleurs primaires :
      - Science Purple #B97FE5 — violet distinctif, neuroscience
      - Bleu Ciel #92ABFB — rassurant, données, interfaces
      - Orange Tonique #FFAD77 — accent, CTA, attention

    Couleurs secondaires :
      - Fond Violet #F7F1FB — fond doux, aérer les espaces
      - Bleu Sérieux #311A4F — titres, footers, fonds d'impact
      - Bleu profond #0E2970
      - Violet vif #3D55DF
      - Rose #FF95FD

    Typo : Helvetica Neue Bold (titres) / Helvetica Neue Regular (corps)
    """
    primary_color: str = "#B97FE5"       # Science Purple — couleur signature
    secondary_color: str = "#FFAD77"     # Orange Tonique — accent / CTA
    bg_color: str = "#FFFFFF"            # Blanc
    text_color: str = "#311A4F"          # Bleu Sérieux — texte principal
    light_text_color: str = "#92ABFB"    # Bleu Ciel — texte secondaire
    accent_bg_color: str = "#F7F1FB"     # Fond Violet — arrière-plans doux
    highlight_color: str = "#3D55DF"     # Violet vif — accents forts
    font_name: str = "Helvetica"         # Helvetica Neue Regular (fallback Helvetica)
    font_name_bold: str = "Helvetica-Bold"  # Helvetica Neue Bold (fallback)
    author_name: str = "Sébastien Tortu"
    author_title: str = "Fondateur @ Boost Conversion"
    logo_text: str = "BOOST CONVERSION"


@dataclass
class CarouselSlide:
    """A single slide in the carousel."""
    slide_type: str  # "title", "content", "stat", "quote", "cta"
    title: str = ""
    body: str = ""
    stat_number: str = ""  # For stat slides
    stat_label: str = ""
    subtitle: str = ""


def _load_brand_from_config() -> BrandConfig:
    """Load brand config from saved file, or return defaults."""
    config_path = Path("/app/brand_config.json")
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text())
            return BrandConfig(
                primary_color=data.get("primary_color", "#B97FE5"),
                secondary_color=data.get("secondary_color", "#FFAD77"),
                bg_color=data.get("bg_color", "#FFFFFF"),
                text_color=data.get("text_color", "#311A4F"),
                light_text_color=data.get("light_text_color", "#92ABFB"),
                accent_bg_color=data.get("accent_bg_color", "#F7F1FB"),
                author_name=data.get("author_name", "Sébastien Tortu"),
                author_title=data.get("author_title", "Fondateur @ Boost Conversion"),
                logo_text=data.get("logo_text", "BOOST CONVERSION"),
            )
        except (json.JSONDecodeError, OSError):
            pass
    return BrandConfig()


def generate_carousel_pdf(
    slides: list[CarouselSlide],
    brand: BrandConfig | None = None,
) -> bytes:
    """Generate a branded PDF carousel from a list of slides.

    Returns the PDF as bytes, ready to upload to LinkedIn.
    """
    if brand is None:
        brand = _load_brand_from_config()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(SLIDE_WIDTH, SLIDE_HEIGHT))

    for i, slide in enumerate(slides):
        if i > 0:
            c.showPage()

        _draw_slide(c, slide, brand, i + 1, len(slides))

    c.save()
    buffer.seek(0)
    return buffer.read()


def _draw_slide(
    c: canvas.Canvas,
    slide: CarouselSlide,
    brand: BrandConfig,
    page_num: int,
    total_pages: int,
):
    """Draw a single slide on the canvas."""
    primary = HexColor(brand.primary_color)
    secondary = HexColor(brand.secondary_color)
    bg = HexColor(brand.bg_color)
    text_color = HexColor(brand.text_color)
    light_text = HexColor(brand.light_text_color)
    accent_bg = HexColor(brand.accent_bg_color)

    # Background
    c.setFillColor(bg)
    c.rect(0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, fill=1, stroke=0)

    margin = 25 * mm
    content_width = SLIDE_WIDTH - 2 * margin

    if slide.slide_type == "title":
        _draw_title_slide(c, slide, brand, primary, secondary, text_color, margin, content_width)
    elif slide.slide_type == "stat":
        _draw_stat_slide(c, slide, brand, primary, secondary, accent_bg, text_color, margin, content_width)
    elif slide.slide_type == "cta":
        _draw_cta_slide(c, slide, brand, primary, secondary, text_color, margin, content_width)
    else:
        _draw_content_slide(c, slide, brand, primary, text_color, light_text, margin, content_width, page_num)

    # Footer: page indicator
    c.setFillColor(light_text)
    c.setFont(brand.font_name, 8)
    c.drawCentredString(SLIDE_WIDTH / 2, 10 * mm, f"{page_num} / {total_pages}")

    # Top bar accent
    c.setFillColor(primary)
    c.rect(0, SLIDE_HEIGHT - 4 * mm, SLIDE_WIDTH, 4 * mm, fill=1, stroke=0)


def _draw_title_slide(c, slide, brand, primary, secondary, text_color, margin, content_width):
    """Title slide: big title + subtitle + author."""
    # Centered layout
    y = SLIDE_HEIGHT * 0.65

    c.setFillColor(primary)
    c.setFont(brand.font_name_bold, 28)
    _draw_wrapped_text(c, slide.title, margin, y, content_width, 28, brand.font_name_bold, max_lines=4)

    if slide.subtitle:
        c.setFillColor(text_color)
        c.setFont(brand.font_name, 14)
        _draw_wrapped_text(c, slide.subtitle, margin, y - 80 * mm, content_width, 14, brand.font_name, max_lines=3)

    # Author block at bottom
    y_author = 35 * mm
    c.setFillColor(secondary)
    c.rect(margin, y_author - 2 * mm, 40 * mm, 3 * mm, fill=1, stroke=0)
    c.setFillColor(text_color)
    c.setFont(brand.font_name_bold, 12)
    c.drawString(margin, y_author - 12 * mm, brand.author_name)
    c.setFillColor(HexColor(brand.light_text_color))
    c.setFont(brand.font_name, 10)
    c.drawString(margin, y_author - 20 * mm, brand.author_title)


def _draw_content_slide(c, slide, brand, primary, text_color, light_text, margin, content_width, page_num):
    """Content slide: number + title + body text."""
    y = SLIDE_HEIGHT - 30 * mm

    # Slide number circle
    c.setFillColor(primary)
    circle_x = margin + 12 * mm
    circle_y = y - 5 * mm
    c.circle(circle_x, circle_y, 12 * mm, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont(brand.font_name_bold, 18)
    c.drawCentredString(circle_x, circle_y - 6, str(page_num - 1))  # -1 because title is page 1

    # Title
    title_y = y - 30 * mm
    c.setFillColor(text_color)
    c.setFont(brand.font_name_bold, 20)
    _draw_wrapped_text(c, slide.title, margin, title_y, content_width, 20, brand.font_name_bold, max_lines=3)

    # Body
    body_y = title_y - 40 * mm
    c.setFillColor(text_color)
    c.setFont(brand.font_name, 13)
    _draw_wrapped_text(c, slide.body, margin, body_y, content_width, 13, brand.font_name, max_lines=8, line_spacing=1.6)


def _draw_stat_slide(c, slide, brand, primary, secondary, accent_bg, text_color, margin, content_width):
    """Stat slide: big number + label."""
    # Accent background
    c.setFillColor(accent_bg)
    c.roundRect(margin, SLIDE_HEIGHT * 0.35, content_width, SLIDE_HEIGHT * 0.35, 8 * mm, fill=1, stroke=0)

    # Big number
    c.setFillColor(primary)
    c.setFont(brand.font_name_bold, 64)
    c.drawCentredString(SLIDE_WIDTH / 2, SLIDE_HEIGHT * 0.55, slide.stat_number)

    # Label
    c.setFillColor(text_color)
    c.setFont(brand.font_name, 16)
    c.drawCentredString(SLIDE_WIDTH / 2, SLIDE_HEIGHT * 0.45, slide.stat_label)

    # Title below
    if slide.title:
        c.setFillColor(text_color)
        c.setFont(brand.font_name_bold, 16)
        _draw_wrapped_text(c, slide.title, margin, SLIDE_HEIGHT * 0.28, content_width, 16, brand.font_name_bold, max_lines=2)


def _draw_cta_slide(c, slide, brand, primary, secondary, text_color, margin, content_width):
    """CTA slide: call to action + author info."""
    y = SLIDE_HEIGHT * 0.6

    c.setFillColor(primary)
    c.setFont(brand.font_name_bold, 24)
    _draw_wrapped_text(c, slide.title, margin, y, content_width, 24, brand.font_name_bold, max_lines=3)

    if slide.body:
        c.setFillColor(text_color)
        c.setFont(brand.font_name, 14)
        _draw_wrapped_text(c, slide.body, margin, y - 50 * mm, content_width, 14, brand.font_name, max_lines=3)

    # CTA button
    btn_y = SLIDE_HEIGHT * 0.25
    btn_w = 120 * mm
    btn_h = 14 * mm
    btn_x = (SLIDE_WIDTH - btn_w) / 2
    c.setFillColor(secondary)
    c.roundRect(btn_x, btn_y, btn_w, btn_h, 7 * mm, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont(brand.font_name_bold, 14)
    c.drawCentredString(SLIDE_WIDTH / 2, btn_y + 4 * mm, slide.subtitle or "En savoir plus")

    # Author
    c.setFillColor(text_color)
    c.setFont(brand.font_name_bold, 12)
    c.drawCentredString(SLIDE_WIDTH / 2, 35 * mm, brand.author_name)
    c.setFillColor(HexColor(brand.light_text_color))
    c.setFont(brand.font_name, 10)
    c.drawCentredString(SLIDE_WIDTH / 2, 27 * mm, brand.author_title)


def _draw_wrapped_text(c, text, x, y, max_width, font_size, font_name, max_lines=5, line_spacing=1.4):
    """Draw text that wraps within max_width."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        if c.stringWidth(test_line, font_name, font_size) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    lines = lines[:max_lines]
    line_height = font_size * line_spacing

    for i, line in enumerate(lines):
        c.drawString(x, y - i * line_height, line)
