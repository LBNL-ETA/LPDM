var uuid = require('uuid/v4');
var check = require('check-types');
var jsonfile = require('jsonfile');
var pool = require('../database');

module.exports = (socket) => {
    socket.on('run_simulation', (scenario_file) => runSimulation(socket, scenario_file));
}

function runSimulation(socket, scenario_file){
    // run the simulation:
    // take the scenario file (either a file name or a string that can be converted into a json object)
    // and write the contents to a temporary text file.
    // call the run_simulation shell script, which makes the call to run the simulation in the docker container
    console.log('run_simulation');
    console.log(check.string(scenario_file));
    if (!check.string(scenario_file)){
        console.log('create temp file');
        console.log(scenario_file);
        jsonfile.writeFile('/simulation/scenarios/node_tmp.json', scenario_file, function (err) {
            console.error(err);
        });
        scenario_file = 'node_tmp.json';
    }
    var last_id = {value: null, closed: false};

    scenario_file = "scenarios/scenario-A1.json"
    let connection_id = uuid();
    const spawn = require('child_process').spawn;
    const ls = spawn(`python`, ['simulation.py'], {env: {CONNECTION_ID: connection_id, SCENARIO_FILE: scenario_file}, cwd: '/simulation' });
    //ls = spawn( 'ls', [ '-lh', '/usr'  ]  );

    let process_running = true;

    ls.stdout.on('data', (data) => {
        console.log(`stdout: ${data}`);
    });

    ls.stderr.on('data', (data) => {
        console.log(`stderr: ${data}`);

    });

    ls.on('close', (code) => {
        console.log(`child process exited with code ${code}`);
        process_running = false;
    });
    setTimeout(() => sendSimulationRun(socket, connection_id), 3000);
    setTimeout(() => querySimulationData(socket, null, last_id, connection_id, process_running), 3000);
}

function sendSimulationRun(socket, connection_id){
    // send the new simulation run info to the client
    pool.connect(function(err, client, done) {
        let query = `
            select id, to_char(time_stamp, 'YYYY-MM-DD HH24:MI') as time_stamp
            from mikey2.sim_run
            where connection_id = $1
        `;

        client.query(query, [connection_id], function(err, result) {
            //call `done(err)` to release the client back to the pool (or destroy it if there is an error)
            done(err);

            if(err) {
                socket.emit("simulation_run_error", err);
            }
            else{
                if (result.rows.length > 0) {
                    socket.emit("simulation_runs", result.rows[0]);
                }
                else {
                    socket.emit("simulation_runs", null);
                }
            }
        });
    });
}

function querySimulationData(socket, id, last_id, connection_id, process_running){
    // stream the new simulation log data to the client
    pool.connect(function(err, client, done) {
        let query = null,
            params = [];
        if (id) {
            query = `
                select run_id, id, device, message, tag, value, time_value, time_string
                from mikey2.sim_log as l
                where run_id = $1
                and device is not null
                and tag is not null
            `;
            params = [id];

        }
        else {
            query = `
                select l.run_id, l.id, l.device, l.message, l.tag, l.value, l.time_value, l.time_string
                from mikey2.sim_log l
                join mikey2.sim_run r on l.run_id = r.id
                where r.connection_id = $1
                and l.device is not null
                and l.tag is not null
            `;
            params = [connection_id];
        }
        if (last_id.value) {
            query = query + " and l.id > $2 "
            params.push(last_id.value);
        }
        query = query + " order by l.id";
        console.log(query);
        console.log(params);

        client.query(query, params, function(err, result) {
            //call `done(err)` to release the client back to the pool (or destroy it if there is an error)
            done(err);
            //console.log('received results');

            if(err) {
                socket.emit("simulation_error", err);
            }
            else{
                console.log(`num rows = ${ result.rows.length }`);
                //console.log(result.rows);
                if (result.rows.length > 0) {
                    //console.log(result.rows[result.rows.length-1]);
                    last_id.value = result.rows[result.rows.length-1].id;
                    socket.emit("simulation_data", result.rows);
                    setTimeout(() => querySimulationData(socket, id, last_id, connection_id, process_running), 1500);
                }
                else {
                    //if (!process_running){
                        socket.emit("simulation_finish");
                        console.log("simulation finished");
                    //}
                    //else{
                        //setTimeout(() => querySimulationData(socket, id, last_id, connection_id, process_running), 1500);
                    //}
                    //setTimeout(() => querySimulationData(socket, err, client, done, id, last_id, connection_id), 1000);
                }
            }
        });
    });
}
