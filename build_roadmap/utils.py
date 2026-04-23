
import re, json


def extract_json(text: str):

    # try code block
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # fallback: try direct
    return json.loads(text)
