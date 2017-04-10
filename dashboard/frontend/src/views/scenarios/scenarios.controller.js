(function() {
    'use strict';
    angular
        .module("lpdmApp")
        .controller("scenariosController", scenariosController);

    scenariosController.$inject = ['$scope', '$state', '$stateParams', 'api', 'socket', 'data_stream'];
    function scenariosController($scope, $state, $stateParams, api, socket, data_stream){
        var ctrl = this;

        ctrl.initialized = false;

        ctrl.scenario = null;
        ctrl.scenario_list = [];

        ctrl.simulation_values = {};

        // setup the socket handlers
        socket.on('scenario_file', receiveSimulationScenarios);
        socket.emit('get_scenario_file');

        // setup the controller functions
        ctrl.selectSimulationScenario = selectSimulationScenario;
        ctrl.newDevice = newDevice;

        ctrl.initialized = true;

        ////

        function receiveSimulationScenarios(data){
            console.log('scenarios...', data);
            for (const sr of data) {
                ctrl.scenario_list.push(sr);
            }
        }


        function selectSimulationScenario(scenario){
            console.log('select scenario', scenario);
            ctrl.scenario = scenario;
        }

        function newDevice(device_type, parent) {
            // add a new device to the parent
            parent.push({
                device_id: "device_x",
                device_type: "grid_controller"
            });
        }

        function runScenario(scenario){
            /// run the selected scenario
            console.log('runScenario', scenario);
            //console.log('run_scenario', scenario);
            //socket.emit('run_simulation', scenario.content);
            //ctrl.is_running = true;
        }
    }
})();
