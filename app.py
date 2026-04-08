import uuid
import subprocess
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, abort
import anthropic

app = Flask(__name__)

UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('outputs')
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

jobs = {}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'video' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['video']
    if not file.filename:
        return jsonify({'error': 'Arquivo inválido'}), 400

    allowed = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        return jsonify({'error': 'Formato não suportado. Use: MP4, MOV, AVI, MKV ou WEBM'}), 400

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > 500 * 1024 * 1024:
        return jsonify({'error': 'Arquivo muito grande. Limite: 500 MB'}), 400

    job_id = str(uuid.uuid4())
    video_path = UPLOAD_FOLDER / f'{job_id}_input{ext}'
    file.save(str(video_path))

    jobs[job_id] = {
        'status': 'queued',
        'current_step': 0,
        'step_name': 'Iniciando processamento...',
        'original_text': '',
        'new_text': '',
        'error': None,
    }

    thread = threading.Thread(
        target=process_video, args=(job_id, str(video_path)), daemon=True
    )
    thread.start()

    return jsonify({'job_id': job_id})


@app.route('/status/<job_id>')
def get_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job não encontrado'}), 404
    return jsonify(job)


@app.route('/download/<job_id>')
def download(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'done':
        abort(404)
    output_path = OUTPUT_FOLDER / f'{job_id}_output.mp4'
    if not output_path.exists():
        abort(404)
    return send_file(
        str(output_path),
        as_attachment=True,
        download_name='video_reescrito.mp4',
        mimetype='video/mp4',
    )


def update_job(job_id, **kwargs):
    if job_id in jobs:
        jobs[job_id].update(kwargs)


def process_video(job_id, video_path):
    audio_path = str(UPLOAD_FOLDER / f'{job_id}_audio.wav')
    new_audio_path = str(UPLOAD_FOLDER / f'{job_id}_new_audio.mp3')

    try:
        # ── Etapa 1: Extrair áudio ─────────────────────────────────────────
        update_job(job_id, status='processing', current_step=1,
                   step_name='Extraindo áudio do vídeo...')

        r = subprocess.run(
            ['ffmpeg', '-i', video_path, '-vn',
             '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
             audio_path, '-y'],
            capture_output=True, text=True, timeout=180,
        )
        if r.returncode != 0:
            raise RuntimeError(
                'Não foi possível extrair o áudio. '
                'Confirme que o vídeo contém trilha de áudio e que o ffmpeg está instalado.'
            )

        # ── Etapa 2: Transcrição com Whisper ──────────────────────────────
        update_job(job_id, current_step=2,
                   step_name='Transcrevendo a fala com Whisper AI...')

        import whisper  # heavy lib — lazy import
        model = whisper.load_model('base')
        transcription = model.transcribe(audio_path, fp16=False)
        original_text = transcription['text'].strip()
        detected_lang = transcription.get('language', 'pt')

        if len(original_text) < 10:
            raise RuntimeError(
                'Não foi possível transcrever o áudio. '
                'Verifique se o vídeo tem fala clara e audível.'
            )

        # ── Etapa 3: Reescrita com Claude ─────────────────────────────────
        update_job(job_id, current_step=3,
                   step_name='Reescrevendo o texto com Claude AI...')

        client = anthropic.Anthropic()
        with client.messages.stream(
            model='claude-opus-4-6',
            max_tokens=4096,
            messages=[{
                'role': 'user',
                'content': (
                    'Você é um especialista em reescrita de textos. '
                    'Reescreva o texto abaixo mantendo:\n'
                    '- O mesmo estilo e tom de voz\n'
                    '- A mesma estrutura e fluxo narrativo\n'
                    '- A mesma intenção e mensagem central\n'
                    f'- O mesmo idioma (idioma detectado: {detected_lang})\n\n'
                    'Use PALAVRAS COMPLETAMENTE DIFERENTES — como uma paráfrase elaborada e natural.\n\n'
                    f'Texto original:\n{original_text}\n\n'
                    'Retorne APENAS o texto reescrito, sem explicações, aspas ou comentários.'
                ),
            }],
        ) as stream:
            response = stream.get_final_message()

        new_text = next(
            (b.text for b in response.content if b.type == 'text'), ''
        ).strip()

        if not new_text:
            raise RuntimeError('A IA não conseguiu gerar o texto reescrito.')

        # ── Etapa 4: Síntese de voz ───────────────────────────────────────
        update_job(job_id, current_step=4,
                   step_name='Sintetizando nova voz...',
                   original_text=original_text, new_text=new_text)

        from gtts import gTTS  # lazy import
        lang_map = {
            'pt': 'pt', 'en': 'en', 'es': 'es',
            'fr': 'fr', 'de': 'de', 'it': 'it',
            'ja': 'ja', 'ko': 'ko', 'zh': 'zh-CN',
        }
        tts_lang = lang_map.get(detected_lang, 'pt')
        gTTS(text=new_text, lang=tts_lang, slow=False).save(new_audio_path)

        # ── Etapa 5: Montar vídeo final ───────────────────────────────────
        update_job(job_id, current_step=5,
                   step_name='Montando o vídeo final...')

        output_path = str(OUTPUT_FOLDER / f'{job_id}_output.mp4')
        r = subprocess.run(
            ['ffmpeg',
             '-i', video_path,
             '-i', new_audio_path,
             '-c:v', 'copy',
             '-map', '0:v:0',
             '-map', '1:a:0',
             '-shortest',
             output_path, '-y'],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode != 0:
            raise RuntimeError('Erro ao montar o vídeo final com o novo áudio.')

        update_job(
            job_id,
            status='done',
            current_step=5,
            step_name='Concluído com sucesso!',
            original_text=original_text,
            new_text=new_text,
        )

    except Exception as exc:
        update_job(job_id, status='error', error=str(exc))

    finally:
        for tmp in [audio_path, new_audio_path]:
            try:
                Path(tmp).unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == '__main__':
    app.run(debug=True, port=5000)
