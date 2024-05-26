const fetchWithRetries = async (url, options, retries = 3, delay = 1000) => {
    for (let i = 0; i < retries; i++) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Attempt ${i + 1} failed: ${error.message}`);
            if (i < retries - 1) {
                await new Promise(res => setTimeout(res, delay));
            } else {
                throw error;
            }
        }
    }
};

const Client = (server, token) => {

    const permissions = async () =>
        fetchWithRetries(`${server}/api/permissions`, {
            headers: {
                'Authorization': token
            }
        }).catch(error => {
            console.error(error);
            return {error: error.message};
        });

    const sections = {
        get: async () =>
            fetchWithRetries(`${server}/api/sections`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        save: async ({comune, sezione, values}) =>
            fetch(`${server}/api/sections`, {
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
            fetchWithRetries(`${server}/api/rdl/emails`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        sections: async () =>
            fetchWithRetries(`${server}/api/rdl/sections`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        assign: async ({comune, sezione, email}) =>
            fetch(`${server}/api/rdl/assign`, {
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
            fetch(`${server}/api/rdl/unassign`, {
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
            fetchWithRetries(`${server}/api/kpi/dati`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        sezioni: () =>
            fetchWithRetries(`${server}/api/kpi/sezioni`, {
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
            fetchWithRetries(`${server}/api/election/lists`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        candidates: async () =>
            fetchWithRetries(`${server}/api/election/candidates`, {
                headers: {
                    'Authorization': token
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
    }

    return {permissions, election, sections, rdl, kpi};
}

export default Client;