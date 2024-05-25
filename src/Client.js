const Client = (server, user, token) => {
    if (!token || !user) {
        return {
            get: () => Promise.reject(new Error('token is required')),
            update: () => Promise.reject(new Error('token is required')),
            append: () => Promise.reject(new Error('token is required')),
            permissions: () => Promise.resolve({
                sections: false,
                referenti: false,
                kpi: false
            }),
            email: '',
            fullName: ''
        };
    }

    const get = ({range}) => {
        return fetch(`${server}/api/sheets/values?range=${range}`, {
            headers: {
                'Authorization': token
            }
        })
            .then(response => response.json())
            .catch(error => {
                console.error(error);
                return {error: error.message};
            });
    }

    const update = ({range, valueInputOption, values}) => {
        return fetch(`${server}/api/sheets/values/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': token
            },
            body: JSON.stringify({range, valueInputOption, values})
        })
            .then(response => response.json())
            .catch(error => {
                console.error(error);
                return {error: error.message};
            });
    }

    const append = ({range, valueInputOption, values}) => {
        return fetch(`${server}/api/sheets/values/append`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': token
            },
            body: JSON.stringify({range, valueInputOption, values})
        })
            .then(response => response.json())
            .catch(error => {
                console.error(error);
                return {error: error.message};
            });
    }

    const profile = user.getBasicProfile();
    const email = profile.getEmail();
    const fullName = profile.getName();

    const permissions = async () => {
        let kpi = (await get({range: "KPI!A2:A"})).values.filter((row) => row[0] === email).length > 0;
        let referenti = (await get({range: "Referenti!A2:A"})).values.filter((row) => row[0] === email).length > 0;
        let sections = referenti || (await get({range: "Dati!C2:C"})).values.filter((row) => row[0] === email).length > 0;
        return { sections, referenti, kpi };
    }

    return { get, update, append, permissions, email, fullName };
}

export default Client;