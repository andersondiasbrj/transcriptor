# Manual de Instalação — Audio Forensic Transcriber

**Versão 1.3.0**  
**Desenvolvedor:** ANDERSON DIAS  
**Suporte:** andersondiasperitoforense@gmail.com

## 1. Requisitos

- Windows 10 ou Windows 11 (64 bits recomendado).
- Espaço livre em disco para o programa, arquivos de trabalho e modelos de transcrição.
- FFmpeg e FFprobe instalados e acessíveis pelo `PATH` do Windows para análise/transcrição de áudio e vídeo.
- Conexão com a internet no primeiro uso de um modelo Faster-Whisper, caso o modelo ainda não esteja em cache.

## 2. Instalação pelo instalador

1. Baixe `AudioForensic_Setup.exe` na seção **Releases** do repositório oficial.
2. Clique duas vezes no instalador. Se o Windows solicitar confirmação, confira se o arquivo foi obtido do repositório publicado pelo desenvolvedor.
3. Siga o assistente e escolha a pasta de destino.
4. Marque a opção de criar atalho na Área de Trabalho, se desejar.
5. Ao concluir, abra o aplicativo pelo Menu Iniciar ou pelo atalho.

## 3. Instalação do FFmpeg e FFprobe

O instalador do aplicativo não incorpora FFmpeg/FFprobe nesta versão. Instale uma distribuição confiável do FFmpeg para Windows e configure a pasta `bin` no `PATH` do sistema. Depois, abra um novo Prompt de Comando e valide:

```bat
ffmpeg -version
ffprobe -version
```

Se os comandos não forem reconhecidos, revise a variável `PATH` e reinicie o aplicativo.

## 4. Primeiro uso

1. Abra o Audio Forensic Transcriber.
2. Na aba **Áudio e vídeo**, selecione um arquivo compatível.
3. Escolha o modelo Whisper e o idioma.
4. Inicie a análise e aguarde o processamento.
5. Consulte a pasta de resultados indicada pelo aplicativo.
6. Na aba **WhatsApp**, importe um arquivo `.zip` ou `.txt` criado pela função Exportar conversa do WhatsApp.
7. Gere os relatórios PDF ou imagens da conversa conforme as opções disponíveis.

## 5. Sobre e suporte

No menu **Ajuda > Sobre o aplicativo** estão disponíveis os créditos do desenvolvedor e o e-mail de suporte:

**ANDERSON DIAS**  
**andersondiasperitoforense@gmail.com**

## 6. Solução de problemas

- **FFmpeg/FFprobe não encontrados:** instale-os, configure o `PATH` e reinicie o aplicativo.
- **Modelo Whisper demorando no primeiro uso:** o modelo pode precisar ser baixado; aguarde e mantenha conexão com a internet.
- **Falha ao importar conversa:** confirme que o arquivo foi exportado pelo WhatsApp e que o ZIP contém o TXT da conversa.
- **Mídia não aparece no relatório:** a exportação pode não ter incluído o arquivo ou o nome do anexo pode não corresponder ao registro no TXT.
- **Transcrição incorreta:** confira o áudio original; reconhecimento automático pode errar em ruído, sobreposição de vozes, sotaques e nomes próprios.

## 7. Cuidados periciais

Mantenha os arquivos originais preservados. Registre a origem, data de recebimento, hash e procedimentos realizados conforme o caso concreto. Os PDFs e imagens de conversas são reproduções técnicas dos dados exportados, não capturas nativas do aplicativo. Os resultados gerados não substituem a análise da fonte primária nem, isoladamente, comprovam autoria, integridade no dispositivo ou completude.
