var express = require('express');
var router = express.Router();
var path = require('path');
var pool = require('../database');

router.get('/', function(req, res) {
    pool.connect(function(err, client, done) {
        console.log('pool connect');
        if(err) {
            res.status(500).send("Error fetching client from poo.");
            return console.error('error fetching client from pool', err);
        }
        let query = `select id, to_char(time_stamp, 'YYYY-MM-DD HH24:MI') as time_stamp from mikey2.sim_run order by id desc`;
        client.query(query, null, function(err, result) {
            //call `done(err)` to release the client back to the pool (or destroy it if there is an error)
            done(err);

            if(err) {
                res.status(500).send("Error running query.");
                return console.error('error running query', err);
            }
            res.send(result.rows);
        });
    });
});

module.exports = router;

