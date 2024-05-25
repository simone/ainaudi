const Client = (server, user, token) => {
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

    const permissions = async () =>
        fetch(`${server}/api/permissions`, {
            headers: {
                'Authorization': token
            }
        })
        .then(response => response.json())
        .catch(error => {
            console.error(error);
            return {error: error.message};
        });

    const sections = {
        get: async () =>
            fetch(`${server}/api/sections`, {
                headers: {
                    'Authorization': token
                }
            })
            .then(response => response.json())
            .catch(error => {
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
            })
            .then(response => response.json())
            .catch(error => {
                console.error(error);
                return {error: error.message};
            }),
    }

    return { get, update, append, permissions, email, fullName, sections };
}

export default Client;