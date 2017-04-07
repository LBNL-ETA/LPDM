var express = require('express');
var router = express.Router();
var path = require('path');
var pool = require('../database');

router.get('/:id', function(req, res) {
    pool.connect(function(err, client, done) {
        if(err) {
            return console.error('error fetching client from pool', err);
        }
        let query = `
            select id, device, message, tag, value, time_value, time_string
            from mikey2.sim_log
            where run_id = $1
            and device is not null
            and tag is not null
            order by id
        `;
        client.query(query, [req.params.id], function(err, result) {
            //call `done(err)` to release the client back to the pool (or destroy it if there is an error)
            done(err);

            if(err) {
                return console.error('error running query', err);
            }
            res.send(result.rows);
        });
    });
});
// Get a list of devices and tags avaialable for a given simulation run
router.get('/:id/device', function(req, res) {
    pool.connect(function(err, client, done) {
        if(err) {
            return console.error('error fetching client from pool', err);
        }
        let query = `
            select device,
                (select json_agg(row_to_json(d))
                from (
                    select distinct il.tag
                    from mikey2.sim_log il
                    where il.run_id = $1
                    and il.device = s.device
                    and il.tag is not null
                ) as d
            ) as tags
            from (select distinct device from mikey2.sim_log as s where s.run_id = $1 and s.device is not null) as s
        `;
        client.query(query, [req.params.id], function(err, result) {
            //call `done(err)` to release the client back to the pool (or destroy it if there is an error)
            done(err);

            if(err) {
                return console.error('error running query', err);
            }
            res.send(result.rows);
        });
    });
});

// get the data for a simulation run for a specific device for a specific tag
router.get('/:id/:device_id/:tag', function(req, res) {
    pool.connect(function(err, client, done) {
        if(err) {
            return console.error('error fetching client from pool', err);
        }
        let query = `
            select id, tag, value, time_value, time_string, message
            from mikey2.sim_log l
            where l.run_id = $1
            and l.device = $2
            and l.tag = $3
            order by id
        `;
        client.query(query, [req.params.id, req.params.device_id, req.params.tag], function(err, result) {
            //call `done(err)` to release the client back to the pool (or destroy it if there is an error)
            done(err);

            if(err) {
                return console.error('error running query', err);
            }
            console.log(result.rows);
            res.send(result.rows);
        });
    });
});

module.exports = router;
