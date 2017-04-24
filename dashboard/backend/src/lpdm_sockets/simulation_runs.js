var pool = require('../database');

module.exports = (socket) => {
    socket.on('get_sim_run_log', (id) => sendSimulationRunLog(socket, id));
    socket.on('get_simulation_runs', () => sendSimulationRuns(socket));
    socket.on('remove_sim_run', (sim_run) => removeSimulationRun(socket, sim_run));
}

function sendSimulationRunLog(socket, id){
    // emit the list of simulation runs
    pool.connect(function(err, client, done) {
        let query = `
            select run_id, id, device, message, tag, value, time_value, time_string
            from public.sim_log as l
            where run_id = $1
            and device is not null
            and tag is not null
        `;
        let params = [id];

        client.query(query, params, function(err, result) {
            //call `done(err)` to release the client back to the pool (or destroy it if there is an error)
            done(err);

            if(err) {
                console.log(err);
                socket.emit("sim_run_log_error", err);
            }
            else{
                socket.emit("sim_run_log_success", result.rows);
            }
        });
    });

}


function sendSimulationRuns(socket){
    // emit the list of simulation runs
    pool.connect(function(err, client, done) {
        let query = `
            select id, to_char(time_stamp, 'YYYY-MM-DD HH24:MI') as time_stamp
            from public.sim_run order by time_stamp desc
        `;

        client.query(query, null, function(err, result) {
            //call `done(err)` to release the client back to the pool (or destroy it if there is an error)
            done(err);

            if(err) {
                console.log(err);
                socket.emit("simulation_run_error", err);
            }
            else{
                socket.emit("simulation_runs", result.rows);
            }
        });
    });

}

function removeSimulationRun(socket, sim_run){
    console.log(`remove simulation run ${ sim_run }`);
    pool.connect(function(err, client, done) {
        if (err){
            console.log(err);
            socket.emit("remove_sim_run_error", err);
            done(err);
        }
        else {
            removeSimLog(socket, sim_run, {client: client, done: done});
        }
    });
}

function removeSimLog(socket, sim_run, pg){
    var query = null;
    var params = null;
    if (sim_run == 'all') {
        query = `truncate table sim_log`;
    }
    else {
        query = `delete from sim_log where run_id = $1`;
        params = [+sim_run];
        console.log('delete');
        console.log(params);
    }

    console.log(query);

    pg.client.query(query, params, function(err, result) {
        if (err){
            console.log(err);
            socket.emit("remove_sim_run_error", err);
            pg.done(err);
        }
        else {
            console.log('removeSimRun');
            removeSimRun(socket, sim_run, pg);
        }
    });
}

function removeSimRun(socket, sim_run, pg) {
    var query = null;
    var params = null;
    if (sim_run == 'all') {
        query = `delete from sim_run`;
    }
    else {
        query = `delete from sim_run where id = $1`;
        params = [+sim_run];
    }

    console.log(query);

    pg.client.query(query, params, function(err, result) {
        pg.done(err);

        if (err){
            console.log(err);
            socket.emit("remove_sim_run_error", err);
        }
        else {
            console.log('done');
            socket.emit("remove_sim_run_success", sim_run);
        }
    });
}
