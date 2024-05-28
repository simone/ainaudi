exports.eq = (s1, s2) => {
    // Se entrambi sono undefined o null, ritorna true
    if (s1 == null && s2 == null) {
        return true;
    }
    // Se solo uno di essi è undefined o null, ritorna false
    if (s1 == null || s2 == null) {
        return false;
    }
    // Usa localeCompare solo se entrambe le variabili sono definite
    return s1.localeCompare(s2, undefined, { sensitivity: 'base' }) === 0;
};
