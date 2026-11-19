class ScriptImportError(Exception):
    """Erro base da importação. Cada subclasse define o status HTTP correspondente."""

    status_code = 400


class UnsupportedFileError(ScriptImportError):
    status_code = 415


class InvalidFileContentError(ScriptImportError):
    status_code = 400


class InvalidScriptStructureError(ScriptImportError):
    status_code = 422
