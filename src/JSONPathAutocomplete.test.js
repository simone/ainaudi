import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import JSONPathAutocomplete from './JSONPathAutocomplete';

// Helper function to extract paths (copy from component for testing)
function extractJSONPaths(json, prefix = '$') {
    const paths = [];

    if (json === null || json === undefined) return paths;

    if (Array.isArray(json)) {
        paths.push({
            path: prefix,
            type: 'array',
            sample: `[${json.length} elementi]`
        });

        if (json.length > 0) {
            const itemPaths = extractJSONPaths(json[0], `${prefix}[]`);
            paths.push(...itemPaths);
        }

        return paths;
    }

    if (typeof json === 'object') {
        for (const [key, value] of Object.entries(json)) {
            const currentPath = `${prefix}.${key}`;

            if (value === null) {
                paths.push({ path: currentPath, type: 'null', sample: 'null' });
            } else if (Array.isArray(value)) {
                paths.push({
                    path: currentPath,
                    type: 'array',
                    sample: `[${value.length} elementi]`
                });

                if (value.length > 0) {
                    const itemPaths = extractJSONPaths(value[0], `${currentPath}[]`);
                    paths.push(...itemPaths);
                }
            } else if (typeof value === 'object') {
                const nestedPaths = extractJSONPaths(value, currentPath);
                paths.push(...nestedPaths);
            } else {
                paths.push({
                    path: currentPath,
                    type: typeof value,
                    sample: String(value).length > 50
                        ? String(value).substring(0, 50) + '...'
                        : String(value)
                });
            }
        }
    }

    return paths;
}

describe('extractJSONPaths', () => {
    test('extracts simple object paths', () => {
        const data = {
            delegato: {
                cognome: 'Rossi',
                nome: 'Mario'
            }
        };

        const paths = extractJSONPaths(data);

        expect(paths).toContainEqual({
            path: '$.delegato.cognome',
            type: 'string',
            sample: 'Rossi'
        });

        expect(paths).toContainEqual({
            path: '$.delegato.nome',
            type: 'string',
            sample: 'Mario'
        });
    });

    test('extracts array paths', () => {
        const data = {
            designazioni: [
                {
                    sezione: '001',
                    effettivo: 'Verdi Luigi'
                }
            ]
        };

        const paths = extractJSONPaths(data);

        expect(paths).toContainEqual({
            path: '$.designazioni',
            type: 'array',
            sample: '[1 elementi]'
        });

        expect(paths).toContainEqual({
            path: '$.designazioni[].sezione',
            type: 'string',
            sample: '001'
        });
    });

    test('handles empty JSON', () => {
        const paths = extractJSONPaths({});
        expect(paths).toEqual([]);
    });

    test('handles null values', () => {
        const data = {
            field: null
        };

        const paths = extractJSONPaths(data);

        expect(paths).toContainEqual({
            path: '$.field',
            type: 'null',
            sample: 'null'
        });
    });
});

describe('JSONPathAutocomplete', () => {
    test('renders input field', () => {
        const mockOnChange = jest.fn();

        render(
            <JSONPathAutocomplete
                value=""
                onChange={mockOnChange}
                exampleData={{}}
            />
        );

        expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    test('shows suggestions when typing', async () => {
        const mockOnChange = jest.fn();
        const exampleData = {
            delegato: {
                cognome: 'Rossi',
                nome: 'Mario'
            }
        };

        render(
            <JSONPathAutocomplete
                value=""
                onChange={mockOnChange}
                exampleData={exampleData}
            />
        );

        const input = screen.getByRole('textbox');

        // Type to trigger suggestions
        fireEvent.change(input, { target: { value: '$.del' } });

        await waitFor(() => {
            expect(screen.getByText(/$.delegato.cognome/i)).toBeInTheDocument();
        });
    });

    test('filters suggestions based on input', async () => {
        const mockOnChange = jest.fn();
        const exampleData = {
            delegato: { cognome: 'Rossi' },
            subdelegato: { cognome: 'Bianchi' }
        };

        render(
            <JSONPathAutocomplete
                value=""
                onChange={mockOnChange}
                exampleData={exampleData}
            />
        );

        const input = screen.getByRole('textbox');

        // Type to filter
        fireEvent.change(input, { target: { value: '$.dele' } });

        await waitFor(() => {
            expect(screen.getByText(/$.delegato.cognome/i)).toBeInTheDocument();
            expect(screen.queryByText(/$.subdelegato.cognome/i)).not.toBeInTheDocument();
        });
    });
});
