import React, { useEffect, useState } from 'react';
import { Bar, Pie } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement } from 'chart.js';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import chroma from 'chroma-js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement, ChartDataLabels);


function Kpi({ client, setError }) {
    const [preferencesData, setPreferencesData] = useState({});
    const [listsData, setListaData] = useState({});
    const [percentData, setPercentData] = useState({});
    const [m5sComuneData, setM5sComuneData] = useState({});
    const [sezioneToMunicipio, setSezioneToMunicipio] = useState(new Map());
    const [m5sComuneMunicipioData, setM5sComuneMunicipioData] = useState({});
    const [countdown, setCountdown] = useState(60);
    const [candidates, setCandidates] = useState([]);
    const [lists, setLists] = useState([]);

    useEffect(() => {
        window.scrollTo(0, 0);
        loadSezioniData();
        loadCandidates();
        loadLists();
        const updateCountdown = () => {
            setCountdown((prevCountdown) => {
                if (prevCountdown > 0) {
                    return prevCountdown - 1;
                }
                return 60;
            });
        };
        const countdownInterval = setInterval(updateCountdown, 1000);
        return () => clearInterval(countdownInterval);
    }, []);

    useEffect(() => {
        if (sezioneToMunicipio.size > 0) {
            loadKpiData();
        }
    }, [sezioneToMunicipio, candidates, lists]);

    useEffect(() => {
        if (countdown === 0) {
            loadKpiData();
        }
    }, [countdown]);

    const loadKpiData = () => {
        client.kpi.dati()
            .then(data => {
                const rows = data.values;
                if (rows && rows.length > 0) {
                    processKpiData(rows);
                }
            }).catch(error => {
                console.error('Error fetching KPI data:', error);
                setError(error.error || error.message || error.toString());
            });
    };

    const loadSezioniData = () => {
        client.kpi.sezioni()
            .then(data => {
                const sezioniRows = data.values;
                const newMap = new Map();
                sezioniRows.forEach(({sezione, comune, municipio}) => {
                    if (comune === 'ROMA' && municipio) {
                        newMap.set(sezione, municipio);
                    }
                });
                setSezioneToMunicipio(newMap);
            }).catch(error => {
                console.error('Error fetching Sezioni data:', error);
                setError(error.error || error.message || error.toString());
            });
    };

    const loadCandidates = () => {
        client.election.candidates()
            .then(data => {
                setCandidates(data.values);
            }).catch(error => {
                console.error('Error fetching Candidates data:', error);
                setError(error.error || error.message || error.toString());
            });
    }

    const loadLists = () => {
        client.election.lists()
            .then(data => {
                setLists(data.values);
            }).catch(error => {
                console.error('Error fetching Lists data:', error);
                setError(error.error || error.message || error.toString());
            });
    }

    const stringToColor = (string) => {
        if (string?.startsWith('ROMA')) {
            return '#FF0000';
        }

        let hash = 0;
        for (let i = 0; i < string.length; i++) {
            hash = string.charCodeAt(i) + ((hash << 5) - hash);
        }

        const colorScale = chroma.scale(['#dbe85c', '#FF0000',]).mode('lch').colors(256);
        const index = Math.abs(hash) % colorScale.length;

        return colorScale[index];
    };

    const decimalToRoman = (num) => {
        if (typeof num !== 'number') return false;

        const romanNumeralMap = [
            { value: 1000, numeral: 'M' },
            { value: 900, numeral: 'CM' },
            { value: 500, numeral: 'D' },
            { value: 400, numeral: 'CD' },
            { value: 100, numeral: 'C' },
            { value: 90, numeral: 'XC' },
            { value: 50, numeral: 'L' },
            { value: 40, numeral: 'XL' },
            { value: 10, numeral: 'X' },
            { value: 9, numeral: 'IX' },
            { value: 5, numeral: 'V' },
            { value: 4, numeral: 'IV' },
            { value: 1, numeral: 'I' }
        ];

        let roman = '';

        for (let i = 0; i < romanNumeralMap.length; i++) {
            while (num >= romanNumeralMap[i].value) {
                roman += romanNumeralMap[i].numeral;
                num -= romanNumeralMap[i].value;
            }
        }

        return roman;
    }

    const processKpiData = (rows) => {
        const preferences = Array(candidates.length).fill(0);
        const listsVotes = Array(lists.length).fill(0);

        // indici delle colonne preferenze e liste
        const fP = 9;
        const lP = fP + candidates.length;
        const fL = lP;
        const lL = fL + lists.length;

        rows.forEach(({values}) => {
            values.slice(fP, lP).forEach((value, index) => {
                preferences[index] += parseInt(value || 0, 10);
            });
            values.slice(fL, lL).forEach((value, index) => {
                listsVotes[index] += parseInt(value || 0, 10);
            });
        });
        const sortedPreferences = preferences.map((value, index) => ({ candidate: candidates[index][0], value }))
            .sort((a, b) => b.value - a.value);

        const sortedCandidates = sortedPreferences.map(item => item.candidate);
        const sortedPreferencesData = sortedPreferences.map(item => item.value);

        setPreferencesData({
            labels: sortedCandidates,
            datasets: [
                {
                    label: 'Preferenze per Candidato',
                    data: sortedPreferencesData,
                    backgroundColor: sortedCandidates.map(stringToColor),
                },
            ],
        });

        const sortedLists = listsVotes.map((value, index) => ({ lists: lists[index], value }))
            .sort((a, b) => b.value - a.value);

        const sortedListsLabels = sortedLists.map(item => item.lists[0]);
        const sortedListsColors = sortedLists.map(item => item.lists[1]);
        const sortedListsData = sortedLists.map(item => item.value);

        setListaData({
            labels: sortedListsLabels,
            datasets: [
                {
                    label: 'Voti di Lista',
                    data: sortedListsData,
                    backgroundColor: sortedListsColors,
                },
            ],
        });

        const totalVotes = sortedLists.reduce((sum, item) => sum + item.value, 0);
        const percentData = sortedLists.map(item => ({
            lists: item.lists[0],
            percent: ((item.value / totalVotes) * 100).toFixed(2),
        }));

        const percentLabels = sortedLists.map(item => item.lists[0]);
        const percentValues = percentData.map(item => parseFloat(item.percent));
        const percentColors = sortedLists.map(item => item.lists[1]);
        setPercentData({
            labels: percentLabels,
            datasets: [
                {
                    label: 'Percentuali di Lista',
                    data: percentValues,
                    backgroundColor: percentColors,
                },
            ],
        });

        let l = lists.map(item => item[0]);
        const m5sIndex = l.indexOf('MOVIMENTO 5 STELLE');
        const comuneVotes = new Map();

        rows.forEach(({comune, values}) => {
            const votes = parseInt(values[fL + m5sIndex] || 0, 10);
            comuneVotes.set(comune, (comuneVotes.get(comune) || 0) + votes);
        });

        const sortedComuneData = Array.from(comuneVotes).sort((a, b) => b[1] - a[1]);
        const comuneLabels = sortedComuneData.map(item => item[0]);
        const comuneVotesData = sortedComuneData.map(item => item[1]);
        setM5sComuneData({
            labels: comuneLabels,
            datasets: [{
                label: 'Voti M5S per Comune',
                backgroundColor: comuneLabels.map(stringToColor),
                data: comuneVotesData,
            }],
        });

        const comuneMunicipioVotes = new Map();

        rows.forEach(({comune, sezione, values}) => {
            if (comune.startsWith('ROMA') && sezioneToMunicipio.has(sezione)) {
                const municipio = sezioneToMunicipio.get(sezione);
                const votes = parseInt(values[22 + m5sIndex] || 0, 10);
                comuneMunicipioVotes.set(municipio, (comuneMunicipioVotes.get(municipio) || 0) + votes);
            }
        });

        const sortedComuneMunicipioData = Array.from(comuneMunicipioVotes).sort((a, b) => b[1] - a[1]);
        const comuneMunicipioLabels = sortedComuneMunicipioData.map(item => `ROMA ${decimalToRoman(+item[0])}`);
        const comuneMunicipioVotesData = sortedComuneMunicipioData.map(item => item[1]);

        setM5sComuneMunicipioData({
            labels: comuneMunicipioLabels,
            datasets: [{
                label: 'Voti M5S su ROMA per Municipio',
                backgroundColor: comuneMunicipioLabels.map(stringToColor),
                data: comuneMunicipioVotesData,
            }],
        });

    };

    const options = {
        indexAxis: 'y',
        scales: {
            x: {
                beginAtZero: true
            }
        },
        maintainAspectRatio: false,
        plugins: {
            datalabels: {
                anchor: 'end',
                align: 'end',
                formatter: (value) => value.toLocaleString(),
            },
        },
    };

    const pieOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            tooltip: {
                callbacks: {
                    label: function (context) {
                        const label = context.label || '';
                        const value = context.raw || 0;
                        return `${label}: ${value}%`;
                    }
                }
            },
            datalabels: {
                display: false
            },
            legend: {
                display: true,
                position: "right"
            },
        },
    };

    const rowHeight = 30;
    const baseHeight = 100;

    const preferencesHeight = preferencesData.labels ? (preferencesData.labels.length * rowHeight + baseHeight) : 400;
    const listsHeight = listsData.labels ? (listsData.labels.length * rowHeight + baseHeight) : 400;
    const comuneHeight = m5sComuneData.labels ? (m5sComuneData.labels.length * rowHeight + baseHeight) : 400;
    const municipioHeight = m5sComuneMunicipioData.labels ? (m5sComuneMunicipioData.labels.length * rowHeight + baseHeight) : 400;

    const progress = countdown/60 * 100;

    if (!preferencesData.labels || !listsData.labels) {
        return <div className="card-body d-flex align-items-center justify-content-center"
                    style={{minHeight: '50vh'}}>
            <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
            </div>
        </div>;
    }

    return (
        <>
            <div className="card">
                <div className="card-header bg-info">
                    Visualizza i grafici delle performance elettorali nella sezione KPI. Analizza i
                    dati per le preferenze dei candidati e i voti di lista per valutare l'andamento
                    elettorale.
                </div>
            </div>
            <div className="small" style={{
                position: 'relative',
                top: -20,
                textAlign: "right"
            }}>
                <div className="progress justify-content-end" style={{
                    height: 3,
                    width: '100%'
                }}>
                    <div
                        className="progress-bar progress-bar-inverted"
                        role="progressbar"
                        style={{ width: `${progress}%` }}
                        aria-valuenow={progress}
                        aria-valuemin="0"
                        aria-valuemax="100"
                    >
                    </div>
                </div>
                Prossimo aggiornamento in: {countdown} secondi
            </div>

            <div className="card mb-3">
                <div className="card-header">
                    <h2>Preferenze per Candidato</h2>
                </div>
                <div className="card-body">
                    <div style={{ height: `${preferencesHeight}px` }}>
                        <Bar data={preferencesData} options={options} />
                    </div>
                </div>
            </div>

            <div className="card mb-3">
                <div className="card-header">
                    <h2>Voti di Lista</h2>
                </div>
                <div className="card-body">
                    <div style={{ height: `${listsHeight}px` }}>
                        <Bar data={listsData} options={options} />
                    </div>
                </div>
            </div>

            <div className="card mb-3">
                <div className="card-header">
                    <h2>Percentuali di Lista</h2>
                </div>
                <div className="card-body">
                    <div style={{ height: '400px' }}>
                        <Pie data={percentData} options={pieOptions} />
                    </div>
                </div>
            </div>

            <div className="card mb-3">
                <div className="card-header">
                    <h2>Voti M5S per Comune</h2>
                </div>
                <div className="card-body">
                    <div style={{ height: `${comuneHeight}px` }}>
                        <Bar data={m5sComuneData} options={options} />
                    </div>
                </div>
            </div>

            <div className="card mb-3">
                <div className="card-header">
                    <h2>Voti M5S su ROMA per Municipio</h2>
                </div>
                <div className="card-body">
                    <div style={{ height: `${municipioHeight}px` }}>
                        <Bar data={m5sComuneMunicipioData} options={options} />
                    </div>
                </div>
            </div>
        </>
    );
}

export default Kpi;
