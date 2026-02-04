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

// Clear all cache (useful on logout)
export const clearCache = () => {
    cache.clear();
};

const Client = (server, pdfServer, token) => {
    // Use Bearer token format for JWT
    const authHeader = token ? `Bearer ${token}` : '';

    const permissions = async () =>
        fetchWithCacheAndRetry('permissions', 120)(`${server}/api/permissions`, {
            headers: {
                'Authorization': authHeader
            }
        }).catch(error => {
            console.error(error);
            return {error: error.message};
        });

    const sections = {
        get: async ({assigned}) =>
            fetchWithCacheAndRetry(`${assigned?'assigned':'own'}`, 30)(`${server}/api/sections/${assigned?'assigned':'own'}`, {
                headers: {
                    'Authorization': authHeader
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        save: async (data) =>
            fetchAndInvalidate(['assigned', 'own'])(`${server}/api/sections/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': authHeader
                },
                body: JSON.stringify(data)
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        stats: async () =>
            fetchWithCacheAndRetry('sections.stats', 60)(`${server}/api/sections/stats`, {
                headers: {
                    'Authorization': authHeader
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        upload: async (file) => {
            const formData = new FormData();
            formData.append('file', file);
            return fetch(`${server}/api/sections/upload`, {
                method: 'POST',
                headers: {
                    'Authorization': authHeader
                },
                body: formData
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return {error: error.message};
            });
        },
        update: async (id, data) => {
            return fetch(`${server}/api/sections/${id}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': authHeader
                },
                body: JSON.stringify(data)
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return {error: error.message};
            });
        },
        list: async (comuneId, page = 1, pageSize = 200) => {
            const params = new URLSearchParams({
                comune_id: comuneId,
                page: page,
                page_size: pageSize
            });
            return fetch(`${server}/api/sections/list/?${params}`, {
                headers: {
                    'Authorization': authHeader
                }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return {error: error.message};
            });
        },
    }

    const rdl = {
        emails: async () =>
            fetchWithCacheAndRetry('rdl.emails', 120)(`${server}/api/rdl/emails`, {
                headers: {
                    'Authorization': authHeader
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        sections: async () =>
            fetchWithCacheAndRetry('rdl.sections', 120)(`${server}/api/rdl/sections`, {
                headers: {
                    'Authorization': authHeader
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
                    'Authorization': authHeader
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
                    'Authorization': authHeader
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
                    'Authorization': authHeader
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        sezioni: () =>
            fetchWithCacheAndRetry('sezioni')(`${server}/api/kpi/sezioni`, {
                headers: {
                    'Authorization': authHeader
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
    }

    const election = {
        // List all elections for switcher
        list: async () =>
            fetch(`${server}/api/elections/`, {
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        // Get active election (first future or current)
        active: async () =>
            fetchWithCacheAndRetry('election_active', 300)(`${server}/api/elections/active/`, {
                headers: {
                    'Authorization': authHeader
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),

        // Get specific election by ID
        get: async (id) =>
            fetch(`${server}/api/elections/${id}/`, {
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        // Get specific ballot
        ballot: async (id) =>
            fetch(`${server}/api/elections/ballots/${id}/`, {
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        // Update a ballot
        updateBallot: async (id, data) =>
            fetch(`${server}/api/elections/ballots/${id}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': authHeader
                },
                body: JSON.stringify(data)
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        lists: async () =>
            fetchWithCacheAndRetry('lists', 600)(`${server}/api/election/lists`, {
                headers: {
                    'Authorization': authHeader
                }
            }).catch(error => {
                console.error(error);
                return {error: error.message};
            }),
        candidates: async () =>
            fetchWithCacheAndRetry('candidates', 600)(`${server}/api/election/candidates`, {
                headers: {
                    'Authorization': authHeader
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
                    'Authorization': authHeader
                },
                body: formData
            }).then(response => response.blob()).catch(error => {
                console.error(error);
                return {error: error.message};
            });
        },
    }

    const users = {
        search: async (query) => {
            if (!query || query.length < 2) return { emails: [] };
            return fetch(`${server}/api/auth/users/search/?q=${encodeURIComponent(query)}`, {
                headers: {
                    'Authorization': authHeader
                }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { emails: [] };
            });
        }
    };

    const rdlRegistrations = {
        // Self-registration (public, no auth needed)
        register: async (data) =>
            fetch(`${server}/api/rdl/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        // List registrations (for delegates)
        list: async (filters = {}) => {
            const params = new URLSearchParams();
            if (filters.status) params.append('status', filters.status);
            if (filters.regione) params.append('regione', filters.regione);
            if (filters.provincia) params.append('provincia', filters.provincia);
            if (filters.comune) params.append('comune', filters.comune);
            if (filters.municipio) params.append('municipio', filters.municipio);
            const queryString = params.toString();
            return fetch(`${server}/api/rdl/registrations${queryString ? `?${queryString}` : ''}`, {
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            });
        },

        // Approve registration
        approve: async (id) =>
            fetch(`${server}/api/rdl/registrations/${id}/approve`, {
                method: 'POST',
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        // Reject registration
        reject: async (id, reason) =>
            fetch(`${server}/api/rdl/registrations/${id}/reject`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': authHeader
                },
                body: JSON.stringify({ reason })
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        // Update registration
        update: async (id, data) =>
            fetch(`${server}/api/rdl/registrations/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': authHeader
                },
                body: JSON.stringify(data)
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        // Delete registration
        delete: async (id) =>
            fetch(`${server}/api/rdl/registrations/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        // Import CSV
        import: async (file) => {
            const formData = new FormData();
            formData.append('file', file);
            return fetch(`${server}/api/rdl/registrations/import`, {
                method: 'POST',
                headers: { 'Authorization': authHeader },
                body: formData
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            });
        }
    };

    // API per le Deleghe (quando Django sarà attivo)
    const deleghe = {
        // Ottiene la catena deleghe dell'utente loggato
        miaCatena: async (consultazioneId) => {
            const url = consultazioneId
                ? `${server}/api/delegations/mia-catena/?consultazione=${consultazioneId}`
                : `${server}/api/delegations/mia-catena/`;
            return fetch(url, {
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            });
        },

        // Lista sub-deleghe (ricevute o fatte)
        subDeleghe: {
            list: async (consultazioneId) => {
                const url = consultazioneId
                    ? `${server}/api/delegations/sub-deleghe/?consultazione=${consultazioneId}`
                    : `${server}/api/delegations/sub-deleghe/`;
                return fetch(url, {
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                });
            },

            get: async (id) =>
                fetch(`${server}/api/delegations/sub-deleghe/${id}/`, {
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),

            create: async (data) =>
                fetch(`${server}/api/delegations/sub-deleghe/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': authHeader
                    },
                    body: JSON.stringify(data)
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),

            revoke: async (id) =>
                fetch(`${server}/api/delegations/sub-deleghe/${id}/`, {
                    method: 'DELETE',
                    headers: { 'Authorization': authHeader }
                }).then(response => response.ok ? {} : response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),
        },

        // Designazioni RDL
        designazioni: {
            list: async (consultazioneId) => {
                const url = consultazioneId
                    ? `${server}/api/delegations/designazioni/?consultazione=${consultazioneId}`
                    : `${server}/api/delegations/designazioni/`;
                return fetch(url, {
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                });
            },

            create: async (data) =>
                fetch(`${server}/api/delegations/designazioni/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': authHeader
                    },
                    body: JSON.stringify(data)
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),

            revoke: async (id) =>
                fetch(`${server}/api/delegations/designazioni/${id}/`, {
                    method: 'DELETE',
                    headers: { 'Authorization': authHeader }
                }).then(response => response.ok ? {} : response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),

            sezioniDisponibili: async (filters = {}) => {
                const params = new URLSearchParams();
                if (filters.comune) params.append('comune', filters.comune);
                if (filters.municipio) params.append('municipio', filters.municipio);
                const queryString = params.toString();
                return fetch(`${server}/api/delegations/designazioni/sezioni_disponibili/${queryString ? `?${queryString}` : ''}`, {
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                });
            },

            // RDL approvati disponibili per mappatura
            rdlDisponibili: async (filters = {}) => {
                const params = new URLSearchParams();
                if (filters.comune) params.append('comune', filters.comune);
                if (filters.municipio) params.append('municipio', filters.municipio);
                const queryString = params.toString();
                return fetch(`${server}/api/delegations/designazioni/rdl_disponibili/${queryString ? `?${queryString}` : ''}`, {
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                });
            },

            // Crea mappatura (RDL -> Sezione)
            mappatura: async (rdlRegistrationId, sezioneId, ruolo) =>
                fetch(`${server}/api/delegations/designazioni/mappatura/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': authHeader
                    },
                    body: JSON.stringify({
                        rdl_registration_id: rdlRegistrationId,
                        sezione_id: sezioneId,
                        ruolo: ruolo
                    })
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),

            // Lista bozze da confermare
            bozzeDaConfermare: async (filters = {}) => {
                const params = new URLSearchParams();
                if (filters.comune) params.append('comune', filters.comune);
                if (filters.municipio) params.append('municipio', filters.municipio);
                const queryString = params.toString();
                return fetch(`${server}/api/delegations/designazioni/bozze_da_confermare/${queryString ? `?${queryString}` : ''}`, {
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                });
            },

            // Conferma una bozza
            conferma: async (id) =>
                fetch(`${server}/api/delegations/designazioni/${id}/conferma/`, {
                    method: 'POST',
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),

            // Rifiuta una bozza
            rifiuta: async (id, motivo = '') =>
                fetch(`${server}/api/delegations/designazioni/${id}/rifiuta/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': authHeader
                    },
                    body: JSON.stringify({ motivo })
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),
        },

        // Campagne di reclutamento
        campagne: {
            list: async (consultazioneId) => {
                const url = consultazioneId
                    ? `${server}/api/delegations/campagne/?consultazione=${consultazioneId}`
                    : `${server}/api/delegations/campagne/`;
                return fetch(url, {
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                });
            },

            get: async (id) =>
                fetch(`${server}/api/delegations/campagne/${id}/`, {
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),

            create: async (data) =>
                fetch(`${server}/api/delegations/campagne/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': authHeader
                    },
                    body: JSON.stringify(data)
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),

            update: async (id, data) =>
                fetch(`${server}/api/delegations/campagne/${id}/`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': authHeader
                    },
                    body: JSON.stringify(data)
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),

            delete: async (id) =>
                fetch(`${server}/api/delegations/campagne/${id}/`, {
                    method: 'DELETE',
                    headers: { 'Authorization': authHeader }
                }).then(response => response.ok ? {} : response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),

            // Attiva una campagna
            attiva: async (id) =>
                fetch(`${server}/api/delegations/campagne/${id}/attiva/`, {
                    method: 'POST',
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),

            // Chiude una campagna
            chiudi: async (id) =>
                fetch(`${server}/api/delegations/campagne/${id}/chiudi/`, {
                    method: 'POST',
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),
        }
    };

    // API per le Risorse (Documenti + FAQ)
    const risorse = {
        // Ottiene tutte le risorse filtrate per la consultazione
        list: async (consultazioneId) => {
            const url = consultazioneId
                ? `${server}/api/risorse/?consultazione=${consultazioneId}`
                : `${server}/api/risorse/`;
            return fetch(url, {
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            });
        },

        documenti: {
            list: async (consultazioneId, categoriaId) => {
                let url = `${server}/api/risorse/documenti/?`;
                if (consultazioneId) url += `consultazione=${consultazioneId}&`;
                if (categoriaId) url += `categoria=${categoriaId}`;
                return fetch(url, {
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                });
            },
        },

        faqs: {
            list: async (consultazioneId, categoriaId, search) => {
                let url = `${server}/api/risorse/faqs/?`;
                if (consultazioneId) url += `consultazione=${consultazioneId}&`;
                if (categoriaId) url += `categoria=${categoriaId}&`;
                if (search) url += `search=${encodeURIComponent(search)}`;
                return fetch(url, {
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                });
            },

            get: async (id) =>
                fetch(`${server}/api/risorse/faqs/${id}/`, {
                    headers: { 'Authorization': authHeader }
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),

            vota: async (id, utile) =>
                fetch(`${server}/api/risorse/faqs/${id}/vota/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': authHeader
                    },
                    body: JSON.stringify({ utile })
                }).then(response => response.json()).catch(error => {
                    console.error(error);
                    return { error: error.message };
                }),
        }
    };

    const territorio = {
        regioni: async () =>
            fetch(`${server}/api/territory/regioni/`, {
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        province: async (regioneId) => {
            const params = regioneId ? `?regione=${regioneId}` : '';
            return fetch(`${server}/api/territory/province/${params}`, {
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            });
        },

        comuni: async (provinciaId) => {
            const params = provinciaId ? `?provincia=${provinciaId}` : '';
            return fetch(`${server}/api/territory/comuni/${params}`, {
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            });
        },

        municipi: async (comuneId) =>
            fetch(`${server}/api/territory/comuni/${comuneId}/`, {
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        // Admin CRUD operations for territory management (superuser only)
        admin: {
            // Regioni
            regioni: {
                list: async () =>
                    fetch(`${server}/api/territory/regioni/`, {
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                get: async (id) =>
                    fetch(`${server}/api/territory/regioni/${id}/`, {
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                create: async (data) =>
                    fetch(`${server}/api/territory/regioni/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': authHeader
                        },
                        body: JSON.stringify(data)
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                update: async (id, data) =>
                    fetch(`${server}/api/territory/regioni/${id}/`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': authHeader
                        },
                        body: JSON.stringify(data)
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                delete: async (id) =>
                    fetch(`${server}/api/territory/regioni/${id}/`, {
                        method: 'DELETE',
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.ok ? {} : response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                import: async (file) => {
                    const formData = new FormData();
                    formData.append('file', file);
                    return fetch(`${server}/api/territory/regioni/import_csv/`, {
                        method: 'POST',
                        headers: { 'Authorization': authHeader },
                        body: formData
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    });
                }
            },

            // Province
            province: {
                list: async (filters = {}) => {
                    const params = new URLSearchParams();
                    if (filters.regione) params.append('regione', filters.regione);
                    const queryString = params.toString();
                    return fetch(`${server}/api/territory/province/${queryString ? `?${queryString}` : ''}`, {
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    });
                },

                get: async (id) =>
                    fetch(`${server}/api/territory/province/${id}/`, {
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                create: async (data) =>
                    fetch(`${server}/api/territory/province/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': authHeader
                        },
                        body: JSON.stringify(data)
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                update: async (id, data) =>
                    fetch(`${server}/api/territory/province/${id}/`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': authHeader
                        },
                        body: JSON.stringify(data)
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                delete: async (id) =>
                    fetch(`${server}/api/territory/province/${id}/`, {
                        method: 'DELETE',
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.ok ? {} : response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                import: async (file) => {
                    const formData = new FormData();
                    formData.append('file', file);
                    return fetch(`${server}/api/territory/province/import_csv/`, {
                        method: 'POST',
                        headers: { 'Authorization': authHeader },
                        body: formData
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    });
                }
            },

            // Comuni
            comuni: {
                list: async (filters = {}) => {
                    const params = new URLSearchParams();
                    if (filters.provincia) params.append('provincia', filters.provincia);
                    if (filters.provincia__regione) params.append('provincia__regione', filters.provincia__regione);
                    if (filters.search) params.append('search', filters.search);
                    if (filters.sopra_15000_abitanti !== undefined) params.append('sopra_15000_abitanti', filters.sopra_15000_abitanti);
                    const queryString = params.toString();
                    return fetch(`${server}/api/territory/comuni/${queryString ? `?${queryString}` : ''}`, {
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    });
                },

                get: async (id) =>
                    fetch(`${server}/api/territory/comuni/${id}/`, {
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                create: async (data) =>
                    fetch(`${server}/api/territory/comuni/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': authHeader
                        },
                        body: JSON.stringify(data)
                    }).then(async response => {
                        const json = await response.json();
                        if (!response.ok) {
                            const errorMsg = Object.entries(json).map(([k, v]) => `${k}: ${v}`).join(', ');
                            return { error: errorMsg };
                        }
                        return json;
                    }).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                update: async (id, data) =>
                    fetch(`${server}/api/territory/comuni/${id}/`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': authHeader
                        },
                        body: JSON.stringify(data)
                    }).then(async response => {
                        const json = await response.json();
                        if (!response.ok) {
                            const errorMsg = Object.entries(json).map(([k, v]) => `${k}: ${v}`).join(', ');
                            return { error: errorMsg };
                        }
                        return json;
                    }).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                delete: async (id) =>
                    fetch(`${server}/api/territory/comuni/${id}/`, {
                        method: 'DELETE',
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.ok ? {} : response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                import: async (file) => {
                    const formData = new FormData();
                    formData.append('file', file);
                    return fetch(`${server}/api/territory/comuni/import_csv/`, {
                        method: 'POST',
                        headers: { 'Authorization': authHeader },
                        body: formData
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    });
                }
            },

            // Municipi
            municipi: {
                list: async (filters = {}) => {
                    const params = new URLSearchParams();
                    if (filters.comune) params.append('comune', filters.comune);
                    const queryString = params.toString();
                    return fetch(`${server}/api/territory/municipi/${queryString ? `?${queryString}` : ''}`, {
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    });
                },

                get: async (id) =>
                    fetch(`${server}/api/territory/municipi/${id}/`, {
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                create: async (data) =>
                    fetch(`${server}/api/territory/municipi/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': authHeader
                        },
                        body: JSON.stringify(data)
                    }).then(async response => {
                        const json = await response.json();
                        if (!response.ok) {
                            const errorMsg = Object.entries(json).map(([k, v]) => `${k}: ${v}`).join(', ');
                            return { error: errorMsg };
                        }
                        return json;
                    }).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                update: async (id, data) =>
                    fetch(`${server}/api/territory/municipi/${id}/`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': authHeader
                        },
                        body: JSON.stringify(data)
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                delete: async (id) =>
                    fetch(`${server}/api/territory/municipi/${id}/`, {
                        method: 'DELETE',
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.ok ? {} : response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                import: async (file) => {
                    const formData = new FormData();
                    formData.append('file', file);
                    return fetch(`${server}/api/territory/municipi/import_csv/`, {
                        method: 'POST',
                        headers: { 'Authorization': authHeader },
                        body: formData
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    });
                }
            },

            // Sezioni Elettorali
            sezioni: {
                list: async (filters = {}) => {
                    const params = new URLSearchParams();
                    if (filters.comune) params.append('comune', filters.comune);
                    if (filters.municipio) params.append('municipio', filters.municipio);
                    if (filters.is_attiva !== undefined) params.append('is_attiva', filters.is_attiva);
                    if (filters.comune__provincia) params.append('comune__provincia', filters.comune__provincia);
                    if (filters.comune__provincia__regione) params.append('comune__provincia__regione', filters.comune__provincia__regione);
                    const queryString = params.toString();
                    return fetch(`${server}/api/territory/sezioni/${queryString ? `?${queryString}` : ''}`, {
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    });
                },

                get: async (id) =>
                    fetch(`${server}/api/territory/sezioni/${id}/`, {
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                create: async (data) =>
                    fetch(`${server}/api/territory/sezioni/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': authHeader
                        },
                        body: JSON.stringify(data)
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                update: async (id, data) =>
                    fetch(`${server}/api/territory/sezioni/${id}/`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': authHeader
                        },
                        body: JSON.stringify(data)
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                delete: async (id) =>
                    fetch(`${server}/api/territory/sezioni/${id}/`, {
                        method: 'DELETE',
                        headers: { 'Authorization': authHeader }
                    }).then(response => response.ok ? {} : response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    }),

                import: async (file) => {
                    const formData = new FormData();
                    formData.append('file', file);
                    return fetch(`${server}/api/territory/sezioni/import_csv/`, {
                        method: 'POST',
                        headers: { 'Authorization': authHeader },
                        body: formData
                    }).then(response => response.json()).catch(error => {
                        console.error(error);
                        return { error: error.message };
                    });
                }
            }
        }
    };

    // API per la Mappatura RDL -> Sezioni (operativa, modificabile)
    const mappatura = {
        // Lista sezioni raggruppate per plesso con assegnazioni
        sezioni: async (filters = {}) => {
            const params = new URLSearchParams();
            if (filters.comune_id) params.append('comune_id', filters.comune_id);
            if (filters.municipio_id) params.append('municipio_id', filters.municipio_id);
            if (filters.municipio) params.append('municipio', filters.municipio);  // Numero municipio
            if (filters.plesso) params.append('plesso', filters.plesso);
            if (filters.filter_status) params.append('filter_status', filters.filter_status);
            const queryString = params.toString();
            return fetchWithCacheAndRetry(`mappatura.sezioni.${queryString}`, 30)(
                `${server}/api/mapping/sezioni/${queryString ? `?${queryString}` : ''}`,
                { headers: { 'Authorization': authHeader } }
            ).catch(error => {
                console.error(error);
                return { error: error.message };
            });
        },

        // Lista RDL approvati con le loro sezioni assegnate
        rdl: async (filters = {}) => {
            const params = new URLSearchParams();
            if (filters.comune_id) params.append('comune_id', filters.comune_id);
            if (filters.municipio_id) params.append('municipio_id', filters.municipio_id);
            if (filters.municipio) params.append('municipio', filters.municipio);  // Numero municipio
            if (filters.search) params.append('search', filters.search);
            const queryString = params.toString();
            return fetchWithCacheAndRetry(`mappatura.rdl.${queryString}`, 30)(
                `${server}/api/mapping/rdl/${queryString ? `?${queryString}` : ''}`,
                { headers: { 'Authorization': authHeader } }
            ).catch(error => {
                console.error(error);
                return { error: error.message };
            });
        },

        // Assegna RDL a sezione
        assegna: async (sezioneId, rdlRegistrationId, ruolo = 'RDL') =>
            fetchAndInvalidate([
                'mappatura.sezioni.',
                'mappatura.rdl.'
            ])(`${server}/api/mapping/assegna/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': authHeader
                },
                body: JSON.stringify({
                    sezione_id: sezioneId,
                    rdl_registration_id: rdlRegistrationId,
                    ruolo: ruolo
                })
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        // Rimuove assegnazione
        rimuovi: async (assignmentId) =>
            fetchAndInvalidate([
                'mappatura.sezioni.',
                'mappatura.rdl.'
            ])(`${server}/api/mapping/assegna/${assignmentId}/`, {
                method: 'DELETE',
                headers: { 'Authorization': authHeader }
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        // Assegna RDL a più sezioni (stesso plesso)
        assegnaBulk: async (rdlRegistrationId, sezioniIds, ruolo = 'RDL') =>
            fetchAndInvalidate([
                'mappatura.sezioni.',
                'mappatura.rdl.'
            ])(`${server}/api/mapping/assegna-bulk/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': authHeader
                },
                body: JSON.stringify({
                    rdl_registration_id: rdlRegistrationId,
                    sezioni_ids: sezioniIds,
                    ruolo: ruolo
                })
            }).then(response => response.json()).catch(error => {
                console.error(error);
                return { error: error.message };
            }),

        // Invalida cache mappatura
        invalidateCache: () => {
            // Invalida tutte le chiavi che iniziano con 'mappatura.'
            for (const key of cache.keys()) {
                if (key.startsWith('mappatura.')) {
                    cache.delete(key);
                }
            }
        }
    };

    return {permissions, election, sections, rdl, kpi, pdf, users, rdlRegistrations, deleghe, risorse, territorio, mappatura};
}

export default Client;
