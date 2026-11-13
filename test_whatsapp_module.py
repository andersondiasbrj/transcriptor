import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image

from whatsapp_module import import_whatsapp_export, parse_chat_text
from whatsapp_exporter import export_chat_pdf, export_chat_images


class WhatsAppImportTests(unittest.TestCase):
    def test_parse_common_formats_and_multiline(self):
        text = (
            "15/08/2026, 14:32 - Maria: Oi\n"
            "15/08/2026, 14:33 - João: Tudo bem?\ncontinuação\n"
            "[15/08/2026, 14:34:02] Maria: foto.jpg (arquivo anexado)\n"
        )
        messages = parse_chat_text(text)
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[1].text, "Tudo bem?\ncontinuação")
        self.assertEqual(messages[2].attachment, "foto.jpg")

    def test_zip_import_and_exports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_path = root / "foto.jpg"
            Image.new("RGB", (320, 180), "white").save(image_path, "JPEG")
            archive_path = root / "export.zip"
            with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
                archive.writestr("_chat.txt", "15/08/2026, 14:32 - Maria: foto.jpg (arquivo anexado)\n")
                archive.write(image_path, "foto.jpg")
            result = import_whatsapp_export(archive_path, root / "case")
            self.assertEqual(len(result["messages"]), 1)
            self.assertTrue((root / "case" / "original" / "export.zip").exists())
            out = root / "case" / "exportacoes"
            pdf = export_chat_pdf(result["messages"], result["metadata"], out / "chat.pdf", root / "case")
            png = export_chat_images(result["messages"], result["metadata"], out / "png", "PNG", 12, root / "case")
            jpg = export_chat_images(result["messages"], result["metadata"], out / "jpg", "JPG", 12, root / "case")
            self.assertTrue(pdf.is_file() and pdf.stat().st_size > 0)
            self.assertTrue(png and png[0].is_file())
            self.assertTrue(jpg and jpg[0].is_file())

    def test_txt_import(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            txt = root / "conversa.txt"
            txt.write_text("01/02/2026, 09:10 - Ana: Bom dia\n", encoding="utf-8")
            result = import_whatsapp_export(txt, root / "case")
            self.assertEqual(result["metadata"]["message_count"], 1)


if __name__ == "__main__":
    unittest.main()
