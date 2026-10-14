import json
from flask import request, jsonify, current_app
from app.routes import scripts_bp
from app.services.bddf_processor import process_bddf_request, BddfPayloadError


@scripts_bp.route("/scripts", methods=["POST"])
def upload_script():
    """
    Upload a BDDF file or JSON payload for processing.
    Returns processed script structure for teleprompter.
    """
    try:
        payload = _get_upload_payload()
        result = process_bddf_request(payload)
    except (BddfPayloadError, json.JSONDecodeError, UnicodeDecodeError) as error:
        return jsonify({"erro": str(error)}), 400

    return jsonify(result), 200


def _get_upload_payload():
    file = request.files.get("file")
    if file is not None:
        if not file.filename:
            raise BddfPayloadError("Arquivo não enviado")
        return json.loads(file.read().decode("utf-8"))

    if request.is_json:
        payload = request.get_json(silent=False)
        if payload is None:
            raise BddfPayloadError("Corpo JSON vazio")
        return payload

    raise BddfPayloadError("Envie um arquivo no campo 'file' ou um corpo JSON")