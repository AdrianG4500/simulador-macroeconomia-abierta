import json

def parse_calibration_template(text: str) -> tuple[dict[str, float], list[str]]:
    params = {}
    errors = []
    text = text.strip()

    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
            for k, v in parsed.items():
                params[k] = float(v)
        except Exception as e:
            errors.append(f"JSON Error: {str(e)}")
    else:
        for line_num, line in enumerate(text.split('\n'), 1):
            line = line.split('#')[0].strip()
            if not line:
                continue
            if '=' in line:
                try:
                    k, v = line.split('=', 1)
                    params[k.strip()] = float(v.strip())
                except ValueError:
                    errors.append(f"Línea {line_num}: Valor inválido '{line}'")
            else:
                errors.append(f"Línea {line_num}: Formato incorrecto '{line}' (se espera clave=valor)")

    return params, errors
