var express = require('express');
var router = express.Router();
var path = require('path');
var pool = require('../database');

router.get('/:id/:device/:tag', function(req, res) {
    pool.connect(function(err, client, done) {
        if(err) {
            res.status(500).send("Error fetching client from poo.");
            return console.error('error fetching client from pool', err);
        }
        let query = `
            select time_value, time_string, value
            from sim_log
            where run_id = $1
            and device = $2
            and tag = $3
            order by id
        `;
        client.query(query, [req.params.id, req.params.device, req.params.tag], function(err, result) {
            //call `done(err)` to release the client back to the pool (or destroy it if there is an error)
            done(err);

            if(err) {
                res.status(500).send("Error running query.");
                return console.error('error running query', err);
            }
            let output = "";
            for (row of result.rows){
                output += `${ row.time_value }\t${ row.time_string }\t${ row.value }\n`;
            }
            let file_name = `${ req.params.id }-${ req.params.device.replace(" ", "_") }-${ req.params.tag.replace(" ", "_") }`;
            res.setHeader('Content-disposition', `attachment; filename=${ file_name }`);
            res.setHeader('Content-type', 'text/plain');
            res.charset = 'UTF-8';
            res.write(output);
            res.end();
        });
    });
});

module.exports = router;


