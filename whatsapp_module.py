"""Importação e exportação técnica de conversas exportadas do WhatsApp.

Não acessa o aplicativo nem extrai mensagens diretamente do telefone. Processa
arquivos exportados pelo usuário (TXT ou ZIP) e preserva o arquivo de entrada.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Optional


@dataclass
class ChatMessage:
    index: int
    date: str
    time: str
    sender: str
    text: str
    kind: str = "message"
    attachment: Optional[str] = None


# Formatos mais comuns dos exports Android/iOS, com variações regionais.
MESSAGE_PATTERNS = [
    re.compile(r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)\]\s*(.*)$"),
    re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)\s*[-–]\s*(.*)$"),
    re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)\s*[-–]\s*(.*)$"),
]

MEDIA_MARKERS = (
    "<mídia oculta>", "<media omitted>", "imagem ocultada", "image omitted",
    "vídeo omitido", "video omitted", "áudio ocultado", "audio omitted",
    "arquivo anexado", "documento omitido", "sticker omitido", "figurinha omitida",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_header(payload: str):
    # Participante: mensagem. Se não houver separador, é evento do sistema.
    if ": " in payload:
        sender, body = payload.split(": ", 1)
        if sender and len(sender) <= 100:
            return sender.strip(), body.strip(), "message"
    return "Sistema", payload.strip(), "system"


def parse_chat_text(text: str) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    current = None
    for raw_line in text.replace("\ufeff", "").splitlines():
        line = raw_line.rstrip("\r\n")
        match = None
        for pattern in MESSAGE_PATTERNS:
            match = pattern.match(line)
            if match:
                break
        if match:
            if current:
                messages.append(current)
            date, time, payload = match.groups()
            sender, body, kind = _parse_header(payload)
            current = ChatMessage(len(messages) + 1, date, time, sender, body, kind)
        elif current:
            # Linhas subsequentes pertencem à mensagem anterior.
            current.text += "\n" + line
        elif line.strip():
            # Cabeçalhos e avisos que antecedem a primeira mensagem são mantidos
            # como eventos sem data, em vez de descartados.
            current = ChatMessage(len(messages) + 1, "", "", "Sistema", line.strip(), "system")
    if current:
        messages.append(current)

    for idx, item in enumerate(messages, start=1):
        item.index = idx
        lower = item.text.lower()
        if any(marker in lower for marker in MEDIA_MARKERS):
            item.kind = "media_placeholder"
        # Nome de mídia citado na exportação: mantém o nome, sem presumir que
        # o conteúdo binário esteja presente.
        file_match = re.search(r"([\w .()\-]+\.(?:jpg|jpeg|png|webp|mp4|opus|ogg|m4a|pdf|docx?|xlsx?))", item.text, re.I)
        if file_match:
            item.attachment = file_match.group(1).strip()
    return messages


def _safe_extract_zip(zip_path: Path, destination: Path) -> list[Path]:
    extracted = []
    base = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        if len(infos) > 20000:
            raise ValueError("O ZIP contém quantidade excessiva de arquivos para importação segura.")
        total_uncompressed = sum(info.file_size for info in infos)
        if total_uncompressed > 2 * 1024 * 1024 * 1024:
            raise ValueError("O conteúdo descompactado excede o limite de 2 GB.")
        for info in infos:
            if info.is_dir():
                continue
            # Bloqueia caminhos absolutos, traversal e entradas suspeitas.
            member = PurePosixPath(info.filename.replace("\\", "/"))
            if member.is_absolute() or ".." in member.parts:
                continue
            target = (destination / Path(*member.parts)).resolve()
            if base not in target.parents and target != base:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(target)
    return extracted


def import_whatsapp_export(source_file: str | Path, case_root: str | Path) -> dict:
    source = Path(source_file).resolve()
    case_root = Path(case_root).resolve()
    if not source.is_file():
        raise FileNotFoundError("O arquivo selecionado não existe.")
    if source.suffix.lower() not in {".zip", ".txt"}:
        raise ValueError("Selecione um ZIP ou TXT exportado pelo WhatsApp.")

    case_root.mkdir(parents=True, exist_ok=True)
    originals = case_root / "original"
    extracted_dir = case_root / "arquivos_extraidos"
    originals.mkdir(exist_ok=True)
    shutil.copy2(source, originals / source.name)
    original_copy = originals / source.name
    original_hash = sha256_file(original_copy)

    extracted_files = []
    if source.suffix.lower() == ".zip":
        extracted_files = _safe_extract_zip(original_copy, extracted_dir)
        txt_candidates = [p for p in extracted_files if p.suffix.lower() == ".txt"]
        if not txt_candidates:
            raise ValueError("O ZIP não contém arquivo TXT de conversa exportada.")
        # Prioriza arquivos com 'chat' ou 'conversa' no nome.
        txt_candidates.sort(key=lambda p: (0 if any(k in p.name.lower() for k in ("chat", "conversa")) else 1, len(p.parts)))
        chat_file = txt_candidates[0]
    else:
        chat_file = original_copy

    raw_text = chat_file.read_text(encoding="utf-8-sig", errors="replace")
    messages = parse_chat_text(raw_text)
    if not messages:
        raise ValueError("Não foram identificadas mensagens. Verifique se o TXT está no formato de exportação do WhatsApp.")

    media_files = [p for p in extracted_files if p.suffix.lower() not in {".txt"}]
    media_index = {p.name.lower(): str(p.relative_to(case_root)) for p in media_files}
    for msg in messages:
        if msg.attachment and msg.attachment.lower() in media_index:
            msg.attachment = media_index[msg.attachment.lower()]

    parsed_path = case_root / "conversation.json"
    parsed_path.write_text(json.dumps([asdict(m) for m in messages], ensure_ascii=False, indent=2), encoding="utf-8")
    metadata = {
        "case_id": case_root.name,
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_filename": source.name,
        "source_extension": source.suffix.lower(),
        "source_size_bytes": original_copy.stat().st_size,
        "source_sha256": original_hash,
        "chat_text_filename": chat_file.name,
        "message_count": len(messages),
        "participants": sorted({m.sender for m in messages if m.sender != "Sistema"}),
        "media_files_extracted": len(media_files),
        "messages_with_attachment_reference": sum(bool(m.attachment) for m in messages),
        "notice": (
            "Conteúdo importado de arquivo exportado pelo usuário. A apresentação gerada não é captura nativa do WhatsApp. "
            "Mensagens, datas e mídias devem ser confrontadas com a fonte original e, quando necessário, com o dispositivo."
        ),
    }
    (case_root / "import_report.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"case_dir": str(case_root), "messages": messages, "metadata": metadata, "media_files": media_files}
