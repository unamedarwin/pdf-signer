# app/app.py

import os
import uuid
import time
import logging
import traceback
import tempfile

from flask import Flask, request, send_file, jsonify, g
from pythonjsonlogger import jsonlogger
from pyhanko.sign.signers import SimpleSigner, PdfSignatureMetadata, PdfSigner
from pyhanko.sign.timestamps import HTTPTimeStamper
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

# Logger en format JSON amb request_id
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(request_id)s %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = Flask(__name__)

# Configuració via variables d'entorn
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))
TSA_URL       = os.getenv('TSA_URL', 'http://freetsa.org/tsr')
MAX_RETRIES   = int(os.getenv('MAX_RETRIES', '5'))
INITIAL_DELAY = int(os.getenv('INITIAL_DELAY', '2'))
MAX_DELAY     = int(os.getenv('MAX_DELAY', '30'))

@app.before_request
def assign_request_id():
    g.request_id = str(uuid.uuid4())
    logger.info('Incoming request', extra={
        'request_id': g.request_id,
        'path': request.path
    })

@app.route('/healthz', methods=['GET'])
def healthz():
    return jsonify(status='ok'), 200

@app.route('/sign-pdf', methods=['POST'])
def sign_pdf_endpoint():
    # 1) Comprovació d'arxius
    if 'file' not in request.files or 'cert' not in request.files:
        return jsonify(error="Cal enviar 'file' (PDF) i 'cert' (.pfx)"), 400

    pdf_file = request.files['file']
    cert_file = request.files['cert']
    cert_pass = request.form.get('password', '')

    # 2) Validació MIME i magic header
    if pdf_file.mimetype != 'application/pdf':
        return jsonify(error='El fitxer no és un PDF'), 400
    head = pdf_file.stream.read(5)
    pdf_file.stream.seek(0)
    if head != b'%PDF-':
        return jsonify(error='Capçalera PDF invàlida'), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        in_pdf  = os.path.join(tmpdir, 'in.pdf')
        out_pdf = os.path.join(tmpdir, 'out.pdf')
        pfx     = os.path.join(tmpdir, 'cert.pfx')

        pdf_file.save(in_pdf)
        cert_file.save(pfx)

        # 3) Carrega el PFX directament a SimpleSigner
        try:
            signer = SimpleSigner.load_pkcs12(
                pfx,
                passphrase=cert_pass.encode() if cert_pass else None
            )
        except Exception as e:
            logger.error('Error carregant PFX', extra={
                'request_id': g.request_id,
                'exc': traceback.format_exc()
            })
            return jsonify(error=f"No s'ha pogut llegir el .pfx: {e}"), 400

        # 4) Prepara metadades sense forcing de validació de 'non-repudiation'
        metadata = PdfSignatureMetadata(
            field_name='Signature',
            reason='Signed with attached certificate'
        )
        timestamper = HTTPTimeStamper(TSA_URL)
        pdf_signer = PdfSigner(
            metadata,
            signer,
            timestamper=timestamper
        )

        # 5) Bucle de reintents amb backoff exponencial
        delay = INITIAL_DELAY
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info('Intent de signatura', extra={
                    'request_id': g.request_id,
                    'attempt': attempt
                })
                with open(in_pdf, 'rb') as inf:
                    writer = IncrementalPdfFileWriter(inf)
                    signed_stream = pdf_signer.sign_pdf(writer)
                with open(out_pdf, 'wb') as outf:
                    outf.write(signed_stream.getvalue())
                logger.info('Signatura completada', extra={'request_id': g.request_id})
                return send_file(out_pdf, as_attachment=True, download_name='signed.pdf')
            except Exception as e:
                logger.warning('Error signant PDF', extra={
                    'request_id': g.request_id,
                    'attempt': attempt,
                    'error': str(e)
                })
                if attempt == MAX_RETRIES:
                    logger.error('Màxim reintents assolit', extra={'request_id': g.request_id})
                    return jsonify(
                        error=f"No s'ha pogut signar després de {MAX_RETRIES} intents: {e}"
                    ), 500
                time.sleep(delay)
                delay = min(delay * 2, MAX_DELAY)

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error('Unhandled exception', extra={
        'request_id': getattr(g, 'request_id', None),
        'exc': traceback.format_exc()
    })
    return jsonify(error=str(e)), 500

if __name__ == '__main__':
    # Només per desenvolupament local
    app.run(host='0.0.0.0', port=8000)
