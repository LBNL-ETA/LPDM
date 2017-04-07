var simulation_run = require('./simulation_runs');
var scenario_file = require('./scenario_file');
var run_simulation = require('./run_simulation');

module.exports = (io) => {
    // set up the various socket handlers
    io.on('connection', (socket) => {
        console.log('socket connection..');
        // set up the  data stream for the simulation run list
        simulation_run(socket);
        // set up the data stream for the scenario json files
        scenario_file(socket);
        // set up the data stream for running the simulation
        run_simulation(socket);
    });
}
