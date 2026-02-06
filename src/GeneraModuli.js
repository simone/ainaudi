import React, {useEffect, useState} from 'react';

// Funzione di utilità per ottenere il valore dal localStorage
const getInitialFormData = () => {
    const savedFormData = localStorage.getItem('subdelegato');
    return savedFormData
        ? JSON.parse(savedFormData)
        : {
            'COGNOME E NOME SUBDELEGATO': '',
            'LUOGO DI NASCITA SUBDELEGATO': '',
            'DATA DI NASCITA SUBDELEGATO': '',
            'TIPO DOCUMENTO SUBDELEGATO': '',
            'NUMERO DOCUMENTO SUBDELEGATO': '',
        };
};

const GeneraModuli = ({client, setError}) => {
    const [formData, setFormData] = useState(getInitialFormData);

    const [excelFile, setExcelFile] = useState(null);
    const [formError, setFormError] = useState('');
    const [loading, setLoading] = useState(false);

    // Effetto per salvare il formData nel localStorage quando cambia
    useEffect(() => {
        localStorage.setItem('subdelegato', JSON.stringify(formData));
    }, [formData]);

    const handleInputChange = (e) => {
        const {name, value} = e.target;
        setFormData({
            ...formData,
            [name]: value,
        });
    };

    const handleFileChange = (e) => {
        setExcelFile(e.target.files[0]);
    };

    const handleSubmitIndividuale = async (e) => {
        e.preventDefault();
        if (!excelFile) {
            setFormError('Please upload an Excel file.');
            return;
        }

        setLoading(true);
        setFormError('');

        const formDataToSend = new FormData();
        formDataToSend.append('excel', excelFile);
        formDataToSend.append('replacements', JSON.stringify(formData));
        client.pdf.generate(formDataToSend, 'single').then((response) => {
            const url = window.URL.createObjectURL(new Blob([response]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `Modulo Individuale nomina RDL ROMA ${formData['COGNOME E NOME SUBDELEGATO']}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        }).catch((error) => {
            console.error(error);
            setError('Error generating the PDF.');
        }).finally(() => {
            setLoading(false);
        });
    };

    const handleSubmitRiepilogativo = async (e) => {
        e.preventDefault();
        if (!excelFile) {
            setFormError('Please upload an Excel file.');
            return;
        }

        setLoading(true);
        setFormError('');

        const formDataToSend = new FormData();
        formDataToSend.append('excel', excelFile);
        formDataToSend.append('replacements', JSON.stringify(formData));
        client.pdf.generate(formDataToSend, 'multiple').then((response) => {
            const url = window.URL.createObjectURL(new Blob([response]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `Modulo Riepilogativo nomina RDL ROMA ${formData['COGNOME E NOME SUBDELEGATO']}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        }).catch((error) => {
            console.error(error);
            setError('Error generating the PDF.');
        }).finally(() => {
            setLoading(false);
        });
    };

    return (
        <>
            {/* Page Header */}
            <div className="page-header delegati">
                <div className="page-header-title">
                    <i className="fas fa-file-signature"></i>
                    Designazioni
                </div>
                <div className="page-header-subtitle">
                    Generazione moduli PDF per nomine RDL
                </div>
            </div>

            <p className="alert alert-secondary">
                A norma di legge i dati del subdelegato li deve inserire chi autentica la sua firma,
                possono quindi essere lasciati in bianco.
                Il loro inserimento è utile per la generazione automatica dei moduli e velocizza i
                tempi di compilazione/autentica, ma non è necessario.
            </p>
            <p className="alert alert-warning">
                Questo tool, non memorizza i dati sul server, rimangono solo sul tuo dispositivo.
            </p>
            <form>
                <div className="mb-3">
                    <label className="form-label">Cognome e Nome Subdelegato:</label>
                    <input type="text" className="form-control" name="COGNOME E NOME SUBDELEGATO" value={formData['COGNOME E NOME SUBDELEGATO']}
                           onChange={handleInputChange}/>
                </div>
                <div className="mb-3">
                    <label className="form-label">Luogo di nascita:</label>
                    <input type="text" className="form-control" name="LUOGO DI NASCITA SUBDELEGATO" value={formData['LUOGO DI NASCITA SUBDELEGATO']}
                           onChange={handleInputChange}/>
                </div>
                <div className="mb-3">
                    <label className="form-label">Data di nascita:</label>
                    <input type="date" className="form-control" name="DATA DI NASCITA SUBDELEGATO" value={formData['DATA DI NASCITA SUBDELEGATO']}
                           onChange={handleInputChange}/>
                </div>
                <div className="mb-3">
                    <label className="form-label">Tipo documento:</label>
                    <input type="text" className="form-control" name="TIPO DOCUMENTO SUBDELEGATO" value={formData['TIPO DOCUMENTO SUBDELEGATO']}
                           onChange={handleInputChange}/>
                </div>
                <div className="mb-3">
                    <label className="form-label">Numero documento:</label>
                    <input type="text" className="form-control" name="NUMERO DOCUMENTO SUBDELEGATO" value={formData['NUMERO DOCUMENTO SUBDELEGATO']}
                           onChange={handleInputChange}/>
                </div>
                <div className="mb-3">
                    <label className="form-label">Carica file Excel:</label>
                    <p className="alert alert-info">Il file Excel deve contenere i dati degli RDL e dei Supplenti con 8 colonne dalla A alla H:
                        Comune, Sezione, Cognome e Nome RDL, Luogo e data di nascita RDL, Domicilio RDL,
                        Cognome e Nome SUP, Luogo e data di nascita SUP, Domicilio SUP
                        <br/>
                        <a href="/templates/template assegnazione sezioni.xlsx" download>Scarica il template</a>
                    </p>
                    <input type="file" className="form-control" accept=".xlsx, .xls" onChange={handleFileChange} required/>
                </div>
                <button type="submit" className="btn btn-primary"
                        onClick={handleSubmitIndividuale}
                        disabled={loading}>{loading ? 'Generazione in corso...' : 'Genera Individuale'}</button>
                <button type="submit" className="btn btn-secondary"
                        onClick={handleSubmitRiepilogativo}
                        disabled={loading}>{loading ? 'Generazione in corso...' : 'Genera Riepilogativo'}</button>
            </form>
            {formError && <p className="text-danger mt-3">{formError}</p>}
        </>
    );
};

export default GeneraModuli;
