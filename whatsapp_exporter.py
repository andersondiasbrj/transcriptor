"""Geração de reproduções técnicas em PDF e PNG/JPG de conversa exportada."""
from __future__ import annotations

import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Image as RLImage

PAGE_W, PAGE_H = A4


def _font(size=24, bold=False):
    candidates = [
        r"C:\Windows\Fonts\segoeui.ttf" if not bold else r"C:\Windows\Fonts\segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf" if not bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _wrap(draw, text, font, max_width):
    output = []
    for paragraph in (text or "").splitlines() or [""]:
        words = paragraph.split()
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
                line = test
            else:
                if line:
                    output.append(line)
                line = word
        output.append(line)
    return output or [""]


def export_chat_images(messages, metadata, output_dir, image_format="PNG", messages_per_page=18, media_root=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    image_format = image_format.upper()
    if image_format not in {"PNG", "JPEG", "JPG"}:
        raise ValueError("Formato de imagem inválido.")
    ext = "jpg" if image_format in {"JPEG", "JPG"} else "png"
    font_title, font_body, font_small, font_bold = _font(34, True), _font(22), _font(17), _font(21, True)
    width, height, margin = 1240, 1754, 72
    content_bottom = height - 145
    bubble_width = int(width * 0.76)
    measure = Image.new("RGB", (10, 10), "white")
    measure_draw = ImageDraw.Draw(measure)

    # Paginação por altura estimada, respeitando também o limite solicitado.
    pages, current, used_height = [], [], 178
    for msg in messages:
        lines = _wrap(measure_draw, msg.text or "", font_body, bubble_width - 42)
        bubble_h = 48 + 30 * len(lines) + (28 if (msg.date or msg.time) else 0)
        attachment_path = (Path(media_root) / msg.attachment) if (media_root and msg.attachment) else None
        is_image = bool(attachment_path and attachment_path.is_file() and attachment_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
        if msg.attachment:
            bubble_h += 24 + (150 if is_image else 0)
        required = bubble_h + 14
        if current and (used_height + required > content_bottom or len(current) >= messages_per_page):
            pages.append(current)
            current, used_height = [], 178
        current.append(msg)
        used_height += required
    if current or not pages:
        pages.append(current)

    generated = []
    for page_no, page_messages in enumerate(pages, start=1):
        image = Image.new("RGB", (width, height), "#f3f5f7")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((margin, 42, width-margin, 150), radius=20, fill="#ffffff", outline="#d7dce2", width=2)
        draw.text((margin+28, 62), "CONVERSA EXPORTADA — REPRODUÇÃO TÉCNICA", font=font_title, fill="#17202a")
        participant_line = ", ".join(metadata.get("participants", [])) or "Participantes não identificados"
        draw.text((margin+28, 117), participant_line[:100], font=font_small, fill="#586575")
        y = 178
        for msg in page_messages:
            sender = msg.sender or "Sistema"
            timestamp = f"{msg.date} {msg.time}".strip()
            is_system = msg.kind == "system" or sender == "Sistema"
            bubble_w = int(width * (0.84 if is_system else 0.76))
            body_lines = _wrap(draw, msg.text or "", font_body, bubble_w - 42)
            attachment_path = (Path(media_root) / msg.attachment) if (media_root and msg.attachment) else None
            is_image = bool(attachment_path and attachment_path.is_file() and attachment_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
            bubble_h = 48 + 30 * len(body_lines) + (28 if timestamp else 0) + (24 if msg.attachment else 0) + (150 if is_image else 0)
            x = margin if is_system else (width - margin - bubble_w)
            fill = "#ffffff" if is_system else "#dff4e5"
            draw.rounded_rectangle((x, y, x+bubble_w, y+bubble_h), radius=18, fill=fill, outline="#d5dce3", width=2)
            draw.text((x+20, y+12), sender[:70], font=font_bold, fill="#263238")
            text_y = y + 44
            for line in body_lines:
                draw.text((x+20, text_y), line, font=font_body, fill="#1f2933")
                text_y += 30
            if msg.attachment:
                draw.text((x+20, text_y+2), f"Anexo: {Path(msg.attachment).name}"[:90], font=font_small, fill="#475569")
                if is_image:
                    try:
                        with Image.open(attachment_path) as media:
                            media.thumbnail((bubble_w - 44, 112))
                            image_y = text_y + 24
                            image_x = x + 20
                            image.paste(media.convert("RGB"), (image_x, image_y))
                    except Exception:
                        pass
            if timestamp:
                draw.text((x+bubble_w-220, y+bubble_h-27), timestamp, font=font_small, fill="#667085")
            y += bubble_h + 14
        footer_y = height - 94
        draw.line((margin, footer_y-18, width-margin, footer_y-18), fill="#cbd5e1", width=2)
        draw.text((margin, footer_y), f"Arquivo de origem SHA-256: {metadata.get('source_sha256','')}", font=font_small, fill="#475569")
        draw.text((width-margin-210, footer_y+30), f"Página {page_no}/{len(pages)}", font=font_small, fill="#475569")
        draw.text((margin, height-42), "Reprodução técnica de arquivo exportado. Não corresponde a captura nativa do aplicativo.", font=font_small, fill="#7c2d12")
        path = output_dir / f"conversa_pagina_{page_no:03d}.{ext}"
        if ext == "jpg":
            image.save(path, quality=92, optimize=True)
        else:
            image.save(path, optimize=True)
        generated.append(path)
    return generated

def export_chat_pdf(messages, metadata, output_path, media_root=None):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=14, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#17202a"), spaceAfter=5*mm)
    small = ParagraphStyle("SmallCustom", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#52606d"))
    body = ParagraphStyle("BodyCustom", parent=styles["BodyText"], fontSize=9, leading=12, spaceAfter=1.5*mm)
    sender_style = ParagraphStyle("SenderCustom", parent=body, fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#1f2937"), spaceAfter=1*mm)
    story = [Paragraph("CONVERSA EXPORTADA — REPRODUÇÃO TÉCNICA", title)]
    participants = ", ".join(metadata.get("participants", [])) or "Não identificados"
    story.append(Paragraph(f"<b>Participantes:</b> {escape(participants)}", small))
    story.append(Paragraph(f"<b>Arquivo de origem:</b> {escape(metadata.get('source_filename',''))}", small))
    story.append(Paragraph(f"<b>SHA-256:</b> {escape(metadata.get('source_sha256',''))}", small))
    story.append(Paragraph(f"<b>Mensagens identificadas:</b> {metadata.get('message_count', 0)}", small))
    story.append(Spacer(1, 5*mm))

    for msg in messages:
        timestamp = f"{msg.date} {msg.time}".strip()
        header = f"{escape(msg.sender or 'Sistema')}" + (f" — {escape(timestamp)}" if timestamp else "")
        content = escape(msg.text or "").replace("\n", "<br/>")
        cell = [Paragraph(header, sender_style), Paragraph(content, body)]
        if msg.attachment:
            cell.append(Paragraph(f"<font color='#52606d'>Anexo: {escape(Path(msg.attachment).name)}</font>", small))
            attachment_path = (Path(media_root) / msg.attachment) if media_root else None
            if attachment_path and attachment_path.is_file() and attachment_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                try:
                    media = RLImage(str(attachment_path), width=65*mm, height=45*mm, kind="proportional")
                    cell.append(media)
                except Exception:
                    pass
        bg = colors.HexColor("#f1f5f9") if msg.kind == "system" else colors.HexColor("#e8f5ec")
        table = Table([[cell]], colWidths=[174*mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), bg),
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.extend([KeepTogether([table]), Spacer(1, 2*mm)])

    story.extend([Spacer(1, 5*mm), Paragraph(
        "NOTA METODOLÓGICA: Este documento é uma reprodução técnica elaborada a partir de arquivo exportado pelo usuário. "
        "Não é captura nativa do WhatsApp, não comprova isoladamente autoria, integridade do conteúdo no dispositivo ou completude da conversa. "
        "O arquivo original deve ser preservado e confrontado com a fonte primária sempre que necessário.", small
    )])
    doc.build(story)
    return output_path
