const cache = new Map();

const fetchWithCacheAndRetry = (key, ttl = 60) => async (url, options, retries = 10, delay = 1000) => {
    const now = Date.now();
    const cacheEntry = cache.get(key);

    if (cacheEntry && (now - cacheEntry.timestamp < ttl * 1000)) {
        console.log('Cache hit', key);
        return cacheEntry.data;
    }

    for (let i = 0; i < retries; i++) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            cache.set(key, { data, timestamp: now });
            return data;
        } catch (error) {
            console.error(`Attempt ${i + 1} failed: ${error.message}`);
            if (i < retries - 1) {
                await new Promise(res => setTimeout(res, delay * Math.pow(2, i)));
            } else {
                throw error;
            }
        }
    }
};

const fetchAndInvalidate = (keys) => async (url, options) => {
    if (typeof keys === 'string') {
        keys = [keys];
    }
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        keys.forEach(key => cache.delete(key));
        return response;
    } catch (error) {
        console.error(`Fetch failed: ${error.message}`);
        throw error;
    }
};



const Client = (server, pdfServer, token) => {

    const permissions = async () =>
        fetchWithCacheAndRetry('permissions', 120)(`${server}/api/permissions`, {
            headers: {
                'Authorization': token
            }
        }).catch(error => {
            console.error(error);
            return {error: error.message};
        });

    const sections = {
        get: async ({assigned}) =>
            fetchWithCacheAndRetry(`${assigned?'assigned':'own'}`, 30)(`${server}/api/sections/${assigned?'assigned':'own'}`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        save: async ({comune, sezione, values}) =>
            fetchAndInvalidate(['assigned', 'own'])(`${server}/api/sections`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': token
                },
                body: JSON.stringify({comune, sezione, values})
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
    }

    const rdl = {
        emails: async () =>
            fetchWithCacheAndRetry('rdl.emails', 120)(`${server}/api/rdl/emails`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        sections: async () =>
            fetchWithCacheAndRetry('rdl.sections', 120)(`${server}/api/rdl/sections`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        assign: async ({comune, sezione, email}) =>
            fetchAndInvalidate('rdl.sections')(`${server}/api/rdl/assign`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': token
                },
                body: JSON.stringify({comune, sezione, email})
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        unassign: async ({comune, sezione}) =>
            fetchAndInvalidate('rdl.sections')(`${server}/api/rdl/unassign`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': token
                },
                body: JSON.stringify({comune, sezione})
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
    }

    const kpi = {
        dati: () =>
            fetchWithCacheAndRetry('kpi')(`${server}/api/kpi/dati`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        sezioni: () =>
            fetchWithCacheAndRetry('sezioni')(`${server}/api/kpi/sezioni`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
    }

    const election = {
        lists: async () =>
            fetchWithCacheAndRetry('lists', 600)(`${server}/api/election/lists`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        candidates: async () =>
            fetchWithCacheAndRetry('candidates', 600)(`${server}/api/election/candidates`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
    }

    const pdf = {
        generate: async (formData, type) => {
            console.log('Generating PDF', type, formData);
            return fetch(`${pdfServer}/api/generate/${type}`, {
                method: 'POST',
                headers: {
                    'Authorization': token
                },
                body: formData
            }).then(response => response.blob()).catch(error => {
                console.error(error);
                return {error: error.message};
            });
        },
    }

    return {permissions, election, sections, rdl, kpi, pdf};
}

export default Client;