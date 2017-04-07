var pool = require('../database');

module.exports = (socket) => {
    socket.on('get_simulation_runs', () => sendSimulationRuns(socket));
}

function sendSimulationRuns(socket){
    // emit the list of simulation runs
    pool.connect(function(err, client, done) {
        let query = `
            select id, to_char(time_stamp, 'YYYY-MM-DD HH24:MI') as time_stamp
            from mikey2.sim_run order by time_stamp desc
        `;

        client.query(query, null, function(err, result) {
            //call `done(err)` to release the client back to the pool (or destroy it if there is an error)
            done(err);

            if(err) {
                socket.emit("simulation_run_error", err);
            }
            else{
                socket.emit("simulation_runs", result.rows);
            }
        });
    });

}
