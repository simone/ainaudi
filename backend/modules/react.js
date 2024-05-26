const express = require("express");
const {join} = require("path");
exports.reactModule = ({app}) =>
{
    app.use(express.static(join(__dirname, '..', '..', 'build')));
    app.get('*', (req, res) => {
        res.sendFile(join(__dirname, '..', '..', 'build', 'index.html'));
    });
}