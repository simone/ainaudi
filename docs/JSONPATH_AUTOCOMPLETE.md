# JSONPath Autocomplete Implementation

## Overview

The JSONPath Autocomplete feature provides intelligent suggestions for JSONPath expressions in the PDF Template Editor, making it easier to configure field mappings without memorizing the exact data structure.

## Architecture

### Components

1. **JSONPathAutocomplete.js** - React component with autocomplete UI
2. **Template.variables_schema** - Django JSONField storing example data
3. **TemplateEditorView API** - Returns variables_schema to frontend
4. **Admin Enhancement** - Django admin fieldset for managing schemas

### Data Flow

```
Django Admin: variables_schema (JSON example)
    ↓
API: /api/documents/templates/{id}/editor/
    ↓
TemplateEditor: Loads template with schema
    ↓
JSONPathAutocomplete: Extracts paths from schema
    ↓
User types → Filtered suggestions appear
    ↓
User selects → Path inserted into field
```

## Features

### 1. Dynamic Path Extraction

The component automatically extracts all possible JSONPath expressions from the example data:

```javascript
// Input example data:
{
  "delegato": {
    "cognome": "Rossi",
    "nome": "Mario"
  },
  "designazioni": [
    {"sezione": "001"}
  ]
}

// Extracted paths:
[
  { path: "$.delegato.cognome", type: "string", sample: "Rossi" },
  { path: "$.delegato.nome", type: "string", sample: "Mario" },
  { path: "$.designazioni", type: "array", sample: "[1 elementi]" },
  { path: "$.designazioni[].sezione", type: "string", sample: "001" }
]
```

### 2. Intelligent Filtering

- **Token-based**: Recognizes current token at cursor position
- **Case-insensitive**: Filters suggestions ignoring case
- **Context-aware**: Doesn't suggest inside quoted strings
- **Array notation**: Handles `[]` for array element paths

### 3. Keyboard Navigation

- **↑/↓**: Navigate suggestions
- **Enter/Tab**: Accept selected suggestion
- **Esc**: Close suggestions
- **Type to filter**: Live filtering as you type

### 4. Visual Feedback

- **Type badges**: Shows data type (string, array, number, etc.)
- **Sample values**: Displays example data for each path
- **Highlighted selection**: Clear visual indicator of selected item
- **Position-aware**: Dropdown appears below input without blocking

## Usage

### For Developers

#### Basic Integration

```jsx
import JSONPathAutocomplete from './JSONPathAutocomplete';

function MyComponent() {
    const [jsonpath, setJsonpath] = useState('');

    return (
        <JSONPathAutocomplete
            value={jsonpath}
            onChange={setJsonpath}
            exampleData={template?.variables_schema || {}}
            placeholder="es: $.delegato.cognome"
            required
        />
    );
}
```

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `value` | string | - | Current JSONPath value |
| `onChange` | function | - | Callback when value changes |
| `exampleData` | object | `{}` | Example JSON to extract paths from |
| `placeholder` | string | - | Input placeholder text |
| `className` | string | `""` | Additional CSS classes |
| `disabled` | boolean | `false` | Disable input |
| `required` | boolean | `false` | Mark as required field |

### For Admins

#### Setting Up variables_schema

1. Navigate to Django Admin → Documents → Templates
2. Select a template
3. Find the "Schema Variabili (Autocomplete)" section
4. Paste example JSON representing your data structure:

```json
{
  "delegato": {
    "cognome": "Rossi",
    "nome": "Mario",
    "email": "mario.rossi@m5s.it"
  },
  "designazioni": [
    {
      "sezione": "001",
      "indirizzo": "Via Roma 1"
    }
  ]
}
```

5. Save the template

#### Example Schemas

See `/backend_django/documents/fixtures/example_variables_schema.json` for complete examples:

- **delegation_template_example**: For sub-delegation documents
- **designation_template_example**: For RDL designation documents
- **full_report_example**: For multi-page reports

### For Users

#### Using Autocomplete

1. **Start typing**: Enter `$.` to trigger suggestions
2. **Browse**: Use arrow keys or continue typing to filter
3. **Select**: Press Enter or Tab to insert selected path
4. **Combine**: Build expressions like `$.cognome + " " + $.nome`

#### Tips

- Type partial paths to filter: `$.del` shows only delegato fields
- Array paths show as `$.designazioni[]` for item access
- Each suggestion shows type and sample value
- Works like bash completion in terminal

## Loop Selection Enhancement

### Visual Indicators

When configuring loop fields, the editor provides clear guidance:

#### Canvas Overlay
- **Yellow border** (3px thick) for loop areas
- **🔁 LOOP badge** in overlay label
- **↓ arrow** at bottom-right indicating vertical repetition

#### Info Alert
Shows when loop type is selected:
```
📋 Come funziona il Loop
1. Seleziona solo la PRIMA riga della tabella sul PDF
2. Le righe successive verranno generate automaticamente
3. Ogni riga avrà la stessa altezza della prima
4. Il sistema trasla automaticamente ogni riga verso il basso

Esempio: Se la prima riga è a Y=150 con altezza 20px,
la seconda sarà a Y=170, la terza a Y=190, ecc.
```

#### Help Section
Enhanced help text explains:
- Only select first row
- Height defines row spacing
- Automatic vertical translation
- Example calculations

## Technical Details

### Path Extraction Algorithm

```javascript
function extractJSONPaths(json, prefix = '$') {
    const paths = [];

    // Handle arrays
    if (Array.isArray(json)) {
        paths.push({ path: prefix, type: 'array', sample: `[${json.length} elementi]` });
        if (json.length > 0) {
            // Extract from first item
            paths.push(...extractJSONPaths(json[0], `${prefix}[]`));
        }
        return paths;
    }

    // Handle objects
    if (typeof json === 'object') {
        for (const [key, value] of Object.entries(json)) {
            const currentPath = `${prefix}.${key}`;

            if (Array.isArray(value)) {
                paths.push({ path: currentPath, type: 'array', ... });
                paths.push(...extractJSONPaths(value[0], `${currentPath}[]`));
            } else if (typeof value === 'object') {
                paths.push(...extractJSONPaths(value, currentPath));
            } else {
                paths.push({ path: currentPath, type: typeof value, sample: value });
            }
        }
    }

    return paths;
}
```

### Token Detection

Identifies current JSONPath token at cursor:

```javascript
function getCurrentToken(text, cursorPos) {
    const before = text.substring(0, cursorPos);
    const tokens = before.split(/[\s+]/);  // Split on whitespace and +
    const currentToken = tokens[tokens.length - 1].trim();
    return currentToken.startsWith('$') ? currentToken : '';
}
```

### Quote Detection

Prevents suggestions inside quoted strings:

```javascript
function isInsideQuotes(text, cursorPos) {
    const before = text.substring(0, cursorPos);
    let inSingle = false;
    let inDouble = false;

    for (let i = 0; i < before.length; i++) {
        const char = before[i];
        const prevChar = i > 0 ? before[i - 1] : null;

        if (prevChar === '\\') continue;  // Skip escaped quotes

        if (char === "'" && !inDouble) inSingle = !inSingle;
        else if (char === '"' && !inSingle) inDouble = !inDouble;
    }

    return inSingle || inDouble;
}
```

## Testing

### Unit Tests

```bash
npm test JSONPathAutocomplete.test.js
```

Tests cover:
- Path extraction from various JSON structures
- Component rendering
- Suggestion filtering
- User interactions

### Manual Testing

1. Create a template in Django Admin
2. Add variables_schema with example data
3. Open Template Editor
4. Click "Aggiungi Campo"
5. Type in JSONPath field
6. Verify:
   - Suggestions appear
   - Filtering works
   - Selection inserts correctly
   - Keyboard navigation works

## Future Enhancements

### Potential Improvements

1. **Validation**: Real-time JSONPath syntax validation
2. **Live Preview**: Show evaluated value from example data
3. **Macro Library**: Common patterns like "Full Name"
4. **Multi-loop**: Support for nested loops
5. **Conditional Rendering**: Show/hide based on conditions
6. **History**: Recently used paths
7. **Favorites**: Bookmark commonly used expressions

### Backend Enhancements

1. **Schema Generation**: Auto-generate from serializers
2. **Versioning**: Track schema changes over time
3. **Validation API**: Endpoint to validate JSONPath expressions
4. **Template Library**: Pre-built schemas for common use cases

## Troubleshooting

### No Suggestions Appear

**Cause**: Empty or invalid variables_schema

**Solution**:
1. Check Django Admin → Template → Schema Variabili
2. Ensure valid JSON is present
3. Verify API returns schema: `/api/documents/templates/{id}/editor/`

### Suggestions Don't Match Data

**Cause**: Schema out of sync with actual data structure

**Solution**:
1. Update variables_schema to match current serializer output
2. Use actual generated JSON as example
3. Test with real data generation

### Autocomplete Too Slow

**Cause**: Very large schema with many paths

**Solution**:
1. Limit example data to representative sample
2. Remove deeply nested structures not used
3. Consider pagination for suggestions (not implemented yet)

## Best Practices

### Schema Design

1. **Keep It Representative**: Use realistic example data
2. **Include All Fields**: Cover all possible paths users might need
3. **Show Nulls**: Include null values for optional fields
4. **Document**: Add comments in admin about schema purpose

### Maintenance

1. **Update with Code**: When serializers change, update schema
2. **Version Control**: Track schema in fixture files
3. **Test Coverage**: Verify autocomplete works for all templates
4. **User Feedback**: Monitor which paths are used most

## Resources

- Component: `/src/JSONPathAutocomplete.js`
- Tests: `/src/JSONPathAutocomplete.test.js`
- Examples: `/backend_django/documents/fixtures/example_variables_schema.json`
- User Guide: `/public/LOOP_GUIDE.md`
- Admin: Django Admin → Documents → Templates

## Version History

- **v1.0** (2026-02-05): Initial implementation
  - Basic autocomplete with dynamic path extraction
  - Loop selection visual enhancements
  - Django admin integration
  - Documentation and examples

---

**Author**: Sistema RDL AInaudi
**Last Updated**: 2026-02-05
