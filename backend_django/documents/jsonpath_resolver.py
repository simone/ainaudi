"""
JSONPath resolver con supporto espressioni concatenate.

Sintassi supportate:
- Semplice: $.delegato.cognome
- Concatenata: $.delegato.cognome + " " + $.delegato.nome
- Con literal: $.delegato.cognome + " (Delegato)"
"""
import re


def resolve_jsonpath(expression, data):
    """
    Resolve JSONPath expression with concatenation support.

    Args:
        expression: JSONPath expression or concatenation
                   Examples:
                   - "$.delegato.cognome"
                   - "$.delegato.cognome + ' ' + $.delegato.nome"
                   - "$.comune + ' (' + $.provincia + ')'"
        data: Dict with data to resolve

    Returns:
        str: Resolved value
    """
    if not expression:
        return ""

    # Check if expression contains concatenation operator '+'
    if '+' in expression:
        return _resolve_concatenated(expression, data)

    # Simple JSONPath
    return _resolve_simple(expression, data)


def _resolve_concatenated(expression, data):
    """Resolve concatenated expression."""
    parts = []

    # Split by '+' but preserve strings in quotes
    tokens = re.split(r"(\+|'[^']*'|\"[^\"]*\")", expression)

    for token in tokens:
        token = token.strip()

        if not token or token == '+':
            continue

        # String literal (quoted)
        if (token.startswith("'") and token.endswith("'")) or \
           (token.startswith('"') and token.endswith('"')):
            parts.append(token[1:-1])  # Remove quotes

        # JSONPath
        elif token.startswith('$'):
            value = _resolve_simple(token, data)
            parts.append(str(value) if value is not None else '')

        # Fallback: treat as literal
        else:
            parts.append(token)

    return ''.join(parts)


def _resolve_simple(path, data):
    """
    Resolve simple JSONPath like $.delegato.cognome

    Args:
        path: JSONPath string starting with $.
        data: Dict with data

    Returns:
        Resolved value or None
    """
    if not path.startswith('$.'):
        return None

    keys = path[2:].split('.')
    current = data

    for key in keys:
        if current is None:
            return None

        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and key.isdigit():
            index = int(key)
            current = current[index] if 0 <= index < len(current) else None
        else:
            return None

    return current


def resolve_loop_data(jsonpath, data):
    """
    Resolve loop JSONPath to get list of items.

    Args:
        jsonpath: JSONPath pointing to array (e.g., "$.designazioni")
        data: Dict with data

    Returns:
        list: Resolved array or empty list
    """
    result = _resolve_simple(jsonpath, data)

    if isinstance(result, list):
        return result

    return []


# Example usage and tests
if __name__ == '__main__':
    test_data = {
        'delegato': {
            'cognome': 'Rossi',
            'nome': 'Mario',
            'email': 'mario.rossi@example.com'
        },
        'comune': 'Roma',
        'provincia': 'RM',
        'designazioni': [
            {'sezione': '001', 'effettivo': 'Verdi Luigi'},
            {'sezione': '002', 'effettivo': 'Bianchi Anna'},
        ]
    }

    # Test simple
    assert resolve_jsonpath('$.delegato.cognome', test_data) == 'Rossi'

    # Test concatenation with space
    assert resolve_jsonpath("$.delegato.cognome + ' ' + $.delegato.nome", test_data) == 'Rossi Mario'

    # Test concatenation with literal
    assert resolve_jsonpath("$.comune + ' (' + $.provincia + ')'", test_data) == 'Roma (RM)'

    # Test loop
    assert len(resolve_loop_data('$.designazioni', test_data)) == 2

    print("✅ All tests passed!")
