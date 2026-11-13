import hashlib
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QProgressBar,
    QTextEdit, QVBoxLayout, QWidget, QTabWidget, QGroupBox, QMenuBar, QDialog,
    QDialogButtonBox, QHBoxLayout
)

from forensic_audio import analyze_audio, ffmpeg_available, transcribe_audio
from whatsapp_module import import_whatsapp_export
from whatsapp_exporter import export_chat_pdf, export_chat_images

APP_DIR = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    RESOURCE_DIR = APP_DIR
ASSET_DIR = RESOURCE_DIR / "assets"
APP_NAME = "Audio Forensic Transcriber"
APP_VERSION = "1.3.0"
DEVELOPER_NAME = "ANDERSON DIAS"
SUPPORT_EMAIL = "andersondiasperitoforense@gmail.com"
OUTPUT_DIR = APP_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {
    ".opus", ".ogg", ".mp3", ".wav", ".m4a", ".aac", ".amr",
    ".flac", ".wma", ".mp4", ".mov", ".mkv", ".webm"
}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class AnalysisWorker(QObject):
    progress = Signal(int, str)
    completed = Signal(str, str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, source, model, language):
        super().__init__()
        self.source = Path(source)
        self.model = model
        self.language = language

    @Slot()
    def run(self):
        try:
            if not ffmpeg_available():
                raise RuntimeError("FFmpeg/FFprobe não encontrados. Instale-os e adicione ao PATH do Windows.")
            if not self.source.exists():
                raise RuntimeError("O arquivo selecionado não existe mais.")
            if self.source.suffix.lower() not in ALLOWED_EXTENSIONS:
                raise RuntimeError("Formato não suportado.")

            case_id = uuid.uuid4().hex[:12]
            case_dir = OUTPUT_DIR / case_id
            case_dir.mkdir(parents=True, exist_ok=True)
            original_name = self.source.name
            original_copy = case_dir / original_name

            self.progress.emit(2, "Preservando arquivo original...")
            shutil.copy2(self.source, original_copy)
            self.progress.emit(5, "Calculando hash SHA-256 do original...")
            file_hash = sha256_file(original_copy)

            metadata = analyze_audio(original_copy, case_dir, self.progress.emit)
            transcription = transcribe_audio(
                original_copy, case_dir, model_size=self.model,
                language=None if self.language == "Automático" else "pt",
                task="transcribe", progress_callback=self.progress.emit
            )

            self.progress.emit(96, "Montando relatório e salvando resultados...")
            report = {
                "case_id": case_id,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "original_filename": original_name,
                "original_extension": self.source.suffix.lower(),
                "sha256": file_hash,
                "metadata": metadata,
                "transcription": transcription,
                "notice": "Transcrição automática auxiliar; revisar o conteúdo com o áudio original."
            }
            (case_dir / "report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self.progress.emit(100, "Análise concluída.")
            self.completed.emit(str(case_dir), file_hash)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — Desktop")
        icon_path = ASSET_DIR / "audio_forensic.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1100, 780)
        self.thread = None
        self.worker = None
        self.last_output = None
        self.whatsapp_case = None
        self.whatsapp_messages = None
        self.whatsapp_metadata = None
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #111827; color: #e5e7eb; font-family: Segoe UI; font-size: 10pt; }
            QFrame#panel, QGroupBox { background: #1f2937; border: 1px solid #374151; border-radius: 12px; }
            QGroupBox { margin-top: 12px; padding: 12px; font-weight: 600; }
            QLabel#title { font-size: 21pt; font-weight: 700; color: #f9fafb; }
            QLabel#muted { color: #9ca3af; }
            QLineEdit, QComboBox, QTextEdit { background: #111827; border: 1px solid #4b5563; border-radius: 7px; padding: 9px; color: #f9fafb; }
            QPushButton { background: #2563eb; border: 0; border-radius: 7px; padding: 10px 16px; color: white; font-weight: 600; }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:disabled { background: #4b5563; color: #9ca3af; }
            QPushButton#secondary { background: #374151; }
            QProgressBar { background: #111827; border: 1px solid #4b5563; border-radius: 6px; height: 18px; text-align: center; }
            QProgressBar::chunk { background: #22c55e; border-radius: 5px; }
            QTabWidget::pane { border: 1px solid #374151; border-radius: 10px; }
            QTabBar::tab { background: #1f2937; padding: 12px 20px; margin-right: 4px; border-top-left-radius: 7px; border-top-right-radius: 7px; }
            QTabBar::tab:selected { background: #2563eb; }
        """)
        self._build_ui()
        self._build_menu()

    def _build_menu(self):
        help_menu = self.menuBar().addMenu("Ajuda")
        about_action = help_menu.addAction("Sobre o aplicativo")
        about_action.triggered.connect(self.show_about)

    def show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Sobre o Audio Forensic Transcriber")
        dialog.setMinimumWidth(440)
        layout = QVBoxLayout(dialog)
        heading = QLabel(APP_NAME)
        heading.setStyleSheet("font-size: 18pt; font-weight: 700; color: #111827;")
        layout.addWidget(heading)
        details = QLabel(
            f"Versão: {APP_VERSION}\n\n"
            f"Desenvolvido por: {DEVELOPER_NAME}\n"
            f"Contato para suporte: {SUPPORT_EMAIL}\n\n"
            "Ferramenta de apoio à transcrição e análise técnica de áudio/vídeo "
            "e à organização de conversas exportadas do WhatsApp.\n\n"
            "As transcrições e reproduções geradas são auxiliares e devem ser "
            "confrontadas com os arquivos originais."
        )
        details.setWordWrap(True)
        details.setStyleSheet("color: #111827; font-size: 10pt;")
        layout.addWidget(details)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        header = QVBoxLayout()
        title = QLabel("Audio Forensic Transcriber")
        title.setObjectName("title")
        subtitle = QLabel("Análise técnica, preservação do original, transcrição e conversas exportadas")
        subtitle.setObjectName("muted")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_audio_tab(), "Áudio e vídeo")
        self.tabs.addTab(self._build_whatsapp_tab(), "WhatsApp")
        root.addWidget(self.tabs, 1)

        foot = QLabel("Preserve sempre os arquivos originais. Relatórios e reproduções visuais são auxiliares e devem ser confrontados com a fonte primária.")
        foot.setObjectName("muted")
        foot.setWordWrap(True)
        root.addWidget(foot)
        self.setCentralWidget(central)

    def _build_audio_tab(self):
        page = QWidget()
        root = QVBoxLayout(page)
        panel = QFrame()
        panel.setObjectName("panel")
        form = QGridLayout(panel)
        form.setContentsMargins(18, 18, 18, 18)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)
        form.addWidget(QLabel("Arquivo de áudio/vídeo"), 0, 0, 1, 3)
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Selecione M4A, MP3, WAV, OGG, OPUS, MP4...")
        self.browse_btn = QPushButton("Selecionar arquivo")
        self.browse_btn.setObjectName("secondary")
        self.browse_btn.clicked.connect(self.choose_file)
        form.addWidget(self.file_edit, 1, 0, 1, 2)
        form.addWidget(self.browse_btn, 1, 2)
        form.addWidget(QLabel("Modelo Whisper"), 2, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText("small")
        form.addWidget(self.model_combo, 3, 0)
        form.addWidget(QLabel("Idioma"), 2, 1)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Português", "Automático"])
        form.addWidget(self.language_combo, 3, 1)
        self.start_btn = QPushButton("Iniciar análise")
        self.start_btn.clicked.connect(self.start_analysis)
        form.addWidget(self.start_btn, 3, 2)
        root.addWidget(panel)

        status_panel = QFrame()
        status_panel.setObjectName("panel")
        status_layout = QVBoxLayout(status_panel)
        status_layout.setContentsMargins(18, 16, 18, 16)
        self.status_label = QLabel("Aguardando arquivo.")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        root.addWidget(status_panel)

        result_panel = QFrame()
        result_panel.setObjectName("panel")
        result_layout = QVBoxLayout(result_panel)
        result_layout.setContentsMargins(18, 16, 18, 16)
        result_layout.addWidget(QLabel("Registro de processamento"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(220)
        result_layout.addWidget(self.log)
        actions = QHBoxLayout()
        self.open_folder_btn = QPushButton("Abrir pasta de resultados")
        self.open_folder_btn.setObjectName("secondary")
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.open_folder_btn.setEnabled(False)
        actions.addWidget(self.open_folder_btn)
        actions.addStretch(1)
        result_layout.addLayout(actions)
        root.addWidget(result_panel, 1)
        return page

    def _build_whatsapp_tab(self):
        page = QWidget()
        root = QVBoxLayout(page)
        intro = QLabel(
            "Importe um ZIP ou TXT gerado pela função Exportar conversa do WhatsApp. "
            "O ZIP pode conter mídias exportadas junto com o histórico."
        )
        intro.setWordWrap(True)
        intro.setObjectName("muted")
        root.addWidget(intro)

        import_group = QGroupBox("1. Importar conversa")
        import_layout = QGridLayout(import_group)
        self.whatsapp_file_edit = QLineEdit()
        self.whatsapp_file_edit.setPlaceholderText("Selecione um arquivo .zip ou .txt")
        browse = QPushButton("Selecionar ZIP/TXT")
        browse.setObjectName("secondary")
        browse.clicked.connect(self.choose_whatsapp_file)
        import_btn = QPushButton("Importar e organizar conversa")
        import_btn.clicked.connect(self.import_whatsapp)
        import_layout.addWidget(self.whatsapp_file_edit, 0, 0, 1, 2)
        import_layout.addWidget(browse, 0, 2)
        import_layout.addWidget(import_btn, 1, 2)
        root.addWidget(import_group)

        export_group = QGroupBox("2. Gerar anexos")
        export_layout = QGridLayout(export_group)
        export_layout.addWidget(QLabel("Mensagens por página de imagem"), 0, 0)
        self.messages_per_page = QComboBox()
        self.messages_per_page.addItems(["8", "10", "12", "15", "18", "20"])
        self.messages_per_page.setCurrentText("12")
        export_layout.addWidget(self.messages_per_page, 0, 1)
        self.export_whatsapp_btn = QPushButton("Gerar PDF + PNG + JPG")
        self.export_whatsapp_btn.clicked.connect(self.export_whatsapp)
        self.export_whatsapp_btn.setEnabled(False)
        export_layout.addWidget(self.export_whatsapp_btn, 1, 0, 1, 2)
        root.addWidget(export_group)

        self.whatsapp_summary = QLabel("Nenhuma conversa importada.")
        self.whatsapp_summary.setWordWrap(True)
        self.whatsapp_summary.setObjectName("muted")
        root.addWidget(self.whatsapp_summary)
        self.whatsapp_preview = QTextEdit()
        self.whatsapp_preview.setReadOnly(True)
        self.whatsapp_preview.setPlaceholderText("Prévia das mensagens importadas...")
        root.addWidget(self.whatsapp_preview, 1)
        self.whatsapp_log = QTextEdit()
        self.whatsapp_log.setReadOnly(True)
        self.whatsapp_log.setMaximumHeight(110)
        root.addWidget(self.whatsapp_log)
        return page

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar áudio", "",
            "Áudios e vídeos (*.m4a *.mp3 *.wav *.ogg *.opus *.aac *.amr *.flac *.wma *.mp4 *.mov *.mkv *.webm);;Todos os arquivos (*.*)"
        )
        if path:
            self.file_edit.setText(path)
            self.log.append(f"Arquivo selecionado: {path}")

    def choose_whatsapp_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar exportação do WhatsApp", "",
            "Exportação WhatsApp (*.zip *.txt);;Arquivos ZIP (*.zip);;Arquivos TXT (*.txt)"
        )
        if path:
            self.whatsapp_file_edit.setText(path)

    def import_whatsapp(self):
        source = self.whatsapp_file_edit.text().strip()
        if not source or not Path(source).is_file():
            QMessageBox.warning(self, "Arquivo necessário", "Selecione um arquivo ZIP ou TXT válido.")
            return
        try:
            case_id = "whatsapp_" + uuid.uuid4().hex[:12]
            case_dir = OUTPUT_DIR / case_id
            self.whatsapp_log.append(f"Importando: {source}")
            result = import_whatsapp_export(source, case_dir)
            self.whatsapp_case = Path(result["case_dir"])
            self.whatsapp_messages = result["messages"]
            self.whatsapp_metadata = result["metadata"]
            participants = ", ".join(result["metadata"].get("participants", [])) or "Não identificados"
            self.whatsapp_summary.setText(
                f"Importação concluída | Mensagens: {len(self.whatsapp_messages)} | "
                f"Participantes: {participants} | Mídias extraídas: {len(result['media_files'])}\n"
                f"SHA-256 do arquivo original: {result['metadata']['source_sha256']}\n"
                f"Pasta do caso: {self.whatsapp_case}"
            )
            preview_lines = []
            for msg in self.whatsapp_messages[:250]:
                stamp = f"{msg.date} {msg.time}".strip()
                preview_lines.append(f"[{stamp}] {msg.sender}: {msg.text}")
            if len(self.whatsapp_messages) > 250:
                preview_lines.append(f"\n... prévia limitada às primeiras 250 de {len(self.whatsapp_messages)} mensagens.")
            self.whatsapp_preview.setPlainText("\n\n".join(preview_lines))
            self.export_whatsapp_btn.setEnabled(True)
            self.whatsapp_log.append("Importação concluída. O arquivo original foi preservado e recebeu hash SHA-256.")
            QMessageBox.information(self, "Importação concluída", f"{len(self.whatsapp_messages)} mensagens identificadas.\n\nArquivo original preservado em:\n{self.whatsapp_case / 'original'}")
        except Exception as exc:
            self.whatsapp_log.append(f"ERRO: {exc}")
            QMessageBox.critical(self, "Falha na importação", str(exc))

    def export_whatsapp(self):
        if not self.whatsapp_case or not self.whatsapp_messages:
            QMessageBox.warning(self, "Conversa não importada", "Importe uma conversa antes de exportar.")
            return
        try:
            export_dir = self.whatsapp_case / "exportacoes"
            export_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = export_chat_pdf(self.whatsapp_messages, self.whatsapp_metadata, export_dir / "conversa_whatsapp.pdf", self.whatsapp_case)
            per_page = int(self.messages_per_page.currentText())
            pngs = export_chat_images(self.whatsapp_messages, self.whatsapp_metadata, export_dir / "png", "PNG", per_page, self.whatsapp_case)
            jpgs = export_chat_images(self.whatsapp_messages, self.whatsapp_metadata, export_dir / "jpg", "JPG", per_page, self.whatsapp_case)
            export_manifest = {
                "pdf": str(pdf_path),
                "png_pages": [str(p) for p in pngs],
                "jpg_pages": [str(p) for p in jpgs],
                "messages_per_image_page": per_page,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "notice": self.whatsapp_metadata.get("notice"),
            }
            (export_dir / "export_manifest.json").write_text(json.dumps(export_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            self.whatsapp_log.append(f"Exportação concluída: {pdf_path}; {len(pngs)} PNG; {len(jpgs)} JPG.")
            QMessageBox.information(self, "Exportação concluída", f"PDF, PNG e JPG gerados em:\n{export_dir}")
            import os
            os.startfile(str(export_dir))
        except Exception as exc:
            self.whatsapp_log.append(f"ERRO NA EXPORTAÇÃO: {exc}")
            QMessageBox.critical(self, "Falha na exportação", str(exc))

    def start_analysis(self):
        source = self.file_edit.text().strip()
        if not source:
            QMessageBox.warning(self, "Arquivo necessário", "Selecione um arquivo antes de iniciar.")
            return
        if not Path(source).is_file():
            QMessageBox.warning(self, "Arquivo inválido", "O caminho informado não existe.")
            return
        self.start_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Preparando análise...")
        self.log.append("\n--- Nova análise ---")
        self.thread = QThread()
        self.worker = AnalysisWorker(source, self.model_combo.currentText(), self.language_combo.currentText())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.update_progress)
        self.worker.completed.connect(self.analysis_completed)
        self.worker.failed.connect(self.analysis_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.analysis_finished)
        self.thread.start()

    @Slot(int, str)
    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        self.log.append(f"[{value:3d}%] {message}")

    @Slot(str, str)
    def analysis_completed(self, output_dir, file_hash):
        self.last_output = output_dir
        self.open_folder_btn.setEnabled(True)
        self.log.append(f"\nAnálise concluída.\nSHA-256: {file_hash}\nResultados: {output_dir}")
        self.status_label.setText("Análise concluída com sucesso.")
        QMessageBox.information(self, "Concluído", f"Análise concluída.\n\nResultados salvos em:\n{output_dir}")

    @Slot(str)
    def analysis_failed(self, error):
        self.log.append(f"\nERRO: {error}")
        self.status_label.setText("A análise encontrou um erro.")
        QMessageBox.critical(self, "Falha na análise", error)

    @Slot()
    def analysis_finished(self):
        self.start_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.thread = None
        self.worker = None

    def open_output_folder(self):
        target = self.last_output or str(OUTPUT_DIR)
        if Path(target).exists():
            import os
            os.startfile(str(target))

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    icon_path = ASSET_DIR / "audio_forensic.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
