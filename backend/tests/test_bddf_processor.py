from app.services.bddf_processor import process_bddf_request


def test_extract_lines_preserves_script_slash_punctuation():
    result = process_bddf_request(
        {
            "slugs": [
                {
                    "body": "<p><pi>FALA./</pi></p>\n"
                    "<p><pi>{{RODA VT}}</pi></p>"
                }
            ]
        }
    )

    subblocks = result["programs"][0]["blocks"][0]["subblocks"]
    assert subblocks == [
        {"type": "text", "lines": ["FALA./"]},
        {"type": "technical", "lines": ["{{RODA VT}}"]},
    ]
