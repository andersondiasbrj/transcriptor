# Audio Forensic Transcriber

**Versão:** 1.3.0  
**Desenvolvedor:** ANDERSON DIAS  
**Suporte:** [andersondiasperitoforense@gmail.com](mailto:andersondiasperitoforense@gmail.com)

Aplicativo desktop Windows em Python/PySide6 para transcrição e análise técnica de áudio/vídeo e organização de conversas exportadas do WhatsApp.

## Funcionalidades

- Transcrição de áudio/vídeo com Faster-Whisper.
- Análise de metadados, preservação de cópia do original e cálculo SHA-256.
- Geração de resultados auxiliares em formatos de texto e dados estruturados.
- Importação de conversas exportadas pelo WhatsApp em `.zip` ou `.txt`.
- Extração de arquivos presentes no ZIP, com validação de caminhos.
- Exportação da conversa organizada em PDF e imagens PNG/JPG.

## Instalação para usuários Windows

1. Baixe o pacote de instalação publicado na seção **Releases** do GitHub.
2. Extraia o pacote, se ele estiver compactado.
3. Execute `AudioForensic_Setup.exe`.
4. Siga as etapas do assistente de instalação.
5. Inicie o programa pelo atalho criado no Menu Iniciar ou na Área de Trabalho.

> A distribuição atual requer FFmpeg e FFprobe instalados no Windows e disponíveis no `PATH` para os recursos de áudio/vídeo. Consulte `docs/MANUAL_INSTALACAO.md`.

## Instalação para desenvolvimento

Requisitos: Windows 10/11, Python 3.11 ou 3.12 e FFmpeg/FFprobe.

```bat
install_windows.bat
run_desktop.bat
```

## Gerar executável e instalador

1. Execute `install_windows.bat`.
2. Instale o Inno Setup 6.
3. Execute `build_exe.bat` para gerar a pasta `dist/AudioForensicTranscriber`.
4. Abra `installer/AudioForensicTranscriber.iss` no Inno Setup Compiler e compile o instalador.
5. O instalador será gerado na pasta `release`.

O build PyInstaller usa `--onedir`; não distribua somente o arquivo `.exe` isolado. Distribua a pasta completa criada em `dist` ou o instalador gerado pelo Inno Setup.

## Módulo WhatsApp: escopo e limitações

- O aplicativo processa arquivos exportados pelo usuário; não acessa diretamente a conta, o banco de dados ou o telefone do WhatsApp.
- A estrutura de exportação varia entre Android/iOS, versões, idiomas e configurações. Um formato não reconhecido deve ser tratado como limitação do parser, não como ausência de mensagens.
- Placeholders como “mídia omitida” indicam que a exportação não trouxe o conteúdo. O programa não recupera mídias ausentes.
- A reprodução PDF/PNG/JPG é uma apresentação técnica do arquivo exportado, não uma captura nativa do WhatsApp nem prova isolada de autoria, integridade no dispositivo ou completude da conversa.
- Preserve o arquivo original e, em perícias, confronte os resultados com a fonte primária e documente a cadeia de custódia aplicável.

## Aviso sobre transcrição

A transcrição automática é um recurso auxiliar. Revise o texto com o áudio original, especialmente nomes próprios, números, datas, termos técnicos e trechos de baixa qualidade.

## Créditos e contato

Desenvolvido por **ANDERSON DIAS**. Dúvidas e suporte: **andersondiasperitoforense@gmail.com**.
