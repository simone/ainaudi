import React, { useState } from 'react';

function UploadSezioni({ client, setError }) {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState(null);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            if (!selectedFile.name.endsWith('.csv')) {
                setError('Seleziona un file CSV');
                return;
            }
            setFile(selectedFile);
            setResult(null);
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setError('Seleziona un file prima di caricare');
            return;
        }

        setUploading(true);
        setError(null);
        setResult(null);

        try {
            const res = await client.sections.upload(file);
            if (res.error) {
                setError(res.error);
            } else {
                setResult(res);
            }
        } catch (err) {
            setError(`Errore durante il caricamento: ${err.message}`);
        } finally {
            setUploading(false);
        }
    };

    return (
        <>
            <h4>Carica Sezioni da CSV</h4>

            <div className="card">
                <div className="card-body">
                    <p className="text-muted">
                        Carica un file CSV con le sezioni elettorali. Il file deve avere le seguenti colonne:
                    </p>
                    <ul className="text-muted">
                        <li><strong>SEZIONE</strong>: Numero della sezione</li>
                        <li><strong>COMUNE</strong>: Nome del comune (es. ROMA)</li>
                        <li><strong>MUNICIPIO</strong>: Numero del municipio (opzionale)</li>
                        <li><strong>INDIRIZZO</strong>: Indirizzo del seggio</li>
                    </ul>

                    <div className="mb-3">
                        <label htmlFor="csvFile" className="form-label">Seleziona file CSV</label>
                        <input
                            type="file"
                            className="form-control"
                            id="csvFile"
                            accept=".csv"
                            onChange={handleFileChange}
                            disabled={uploading}
                        />
                    </div>

                    {file && (
                        <p className="text-info">
                            File selezionato: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(1)} KB)
                        </p>
                    )}

                    <button
                        className="btn btn-primary"
                        onClick={handleUpload}
                        disabled={!file || uploading}
                    >
                        {uploading ? (
                            <>
                                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                Caricamento in corso...
                            </>
                        ) : (
                            'Carica Sezioni'
                        )}
                    </button>
                </div>
            </div>

            {result && (
                <div className={`alert ${result.errors?.length ? 'alert-warning' : 'alert-success'} mt-3`}>
                    <h5>Caricamento completato</h5>
                    <ul className="mb-0">
                        <li>Sezioni create: <strong>{result.created}</strong></li>
                        <li>Sezioni aggiornate: <strong>{result.updated}</strong></li>
                        <li>Totale elaborato: <strong>{result.total}</strong></li>
                    </ul>
                    {result.errors?.length > 0 && (
                        <div className="mt-2">
                            <strong>Errori:</strong>
                            <ul className="mb-0">
                                {result.errors.map((err, i) => (
                                    <li key={i} className="text-danger">{err}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}

            <div className="card mt-3">
                <div className="card-header">
                    Esempio formato CSV
                </div>
                <div className="card-body">
                    <pre className="mb-0" style={{ fontSize: '0.85em' }}>
{`SEZIONE,COMUNE,MUNICIPIO,INDIRIZZO
1,ROMA,3,"VIA DI SETTEBAGNI, 231"
2,ROMA,1,"VIA DANIELE MANIN, 72"
3,ROMA,1,"VIA DANIELE MANIN, 72"
...`}
                    </pre>
                </div>
            </div>
        </>
    );
}

export default UploadSezioni;
