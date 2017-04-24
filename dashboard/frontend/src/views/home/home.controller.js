(function() {
    'use strict';
    angular
        .module("lpdmApp")
        .controller("homeController", homeController);

    homeController.$inject = ['$scope', '$state', '$stateParams', 'api', 'socket', 'data_stream'];
    function homeController($scope, $state, $stateParams, api, socket, data_stream){
        var ctrl = this;

        function SimTime(time_value, time_string){
            this.time_value = time_value;
            this.time_string = time_string;
        }

        function SimData(){
            this.times = [];
            this.runs = [];
            this.devices = [];
        }

        function SimDevice(device) {
            this.name = device;
            this.tags = [];
        }

        function SimTag(tag) {
            this.name = tag;
            this.runs = [];
        }

        function SimRun(run_id) {
            this.run_id = run_id;
            this.values = [];
        }

        function SimValue(sim_time, value) {
            this.sim_time = sim_time;
            this.value = value;
        }

        SimData.prototype.addLine = addLine;
        function addLine(line) {
            let self = this;
            // add the distinct times
            let sim_time = self.times.find((item) => item.time_value == line.time_value);
            if (!sim_time) {
                sim_time = new SimTime(line.time_value, line.time_string);
                self.times.push(sim_time);
            }

            // assign the sim_run
            let sim_run = self.runs.find((item) => item.run_id == line.run_id);
            if (!sim_run) {
                sim_run = new SimRun(line.run_id);
                self.runs.push(sim_run);
            }

            // add the device info
            let device = self.devices.find((item) => item.name == line.device);
            if (!device) {
                device = new SimDevice(line.device);
                self.devices.push(device);
            }

            // assign the tag
            let tag = device.tags.find((item) => item.name == line.tag);
            if (!tag) {
                tag = new SimTag(line.tag);
                device.tags.push(tag);
            }

            // assign the sim_run
            let sim_run_tag = tag.runs.find((item) => item.run_id == line.run_id);
            if (!sim_run_tag) {
                sim_run_tag = new SimRun(line.run_id);
                tag.runs.push(sim_run_tag);
            }


            // add the value
            let value = new SimValue(sim_time, line.value);
            sim_run_tag.values.push(value);
        }

        function TagView(device, tag){
            this.device = device;
            this.tag = tag;
        }
        ctrl.selected_tag_views = [];
        ctrl.toggleTagView = toggleTagView;

        ctrl.sim_data = new SimData();

        ctrl.initialized = false;
        ctrl.is_running = false;

        ctrl.progress = 0;

        ctrl.scenario = null;
        ctrl.scenario_list = null;

        ctrl.sim_run = null;
        ctrl.sim_run_list = [];

        ctrl.scenario = null;
        ctrl.scenario_list = [];

        ctrl.selected_run = [];
        ctrl.simulation_data = [];

        ctrl.side_nav_is_open = true;
        ctrl.showNav = showNav;

        ctrl.selectSimulationScenario = selectSimulationScenario;
        ctrl.runScenario = runScenario;
        ctrl.selectSimulationRun = selectSimulationRun;
        ctrl.tagIsSelected = tagIsSelected;
        //ctrl.getSimulationData = getSimulationData;
        ctrl.show_results = false;

        ctrl.data_grid = {
            enableSorting: false,
            enableRowSelection: false,
            enableSelectAll: false,
            showGridFooter: true,
            multiSelect: false,
            enableFiltering: true,
            columnDefs: [
                {
                    name: 'time_string',
                    displayName: 'Time',
                }, {
                    name: 'time_value',
                    displayName: 'Time',
                }, {
                    name: 'device',
                    displayName: 'Device',
                }, {
                    name: 'tag',
                    displayName: 'Tag',
                }, {
                    name: 'value',
                    displayName: 'Value',
                }
            ],
            data: ctrl.simulation_data,
            //onRegisterApi: function(gridApi){
                ////set gridApi on scope
                //gridApi.selection.on.rowSelectionChanged($scope,function(row){
                    //var items = gridApi.selection.getSelectedRows();
                    //if (items.length) {
                        //$scope.selected_item = items[0];
                    //}
                    //else {
                        //$scope.selected_item = null;
                    //}
                //});
            //}
        };

        socket.on('connection', function(data){
            console.log('socket connected!!', data);
        });

        ctrl.selectDeviceTag = selectDeviceTag;

        // setup the array to handle the data from the websocket response
        //data_stream.subscribeToSimulationRun(6, receiveData, receiveError);
        socket.on('simulation_error', receiveError);
        socket.on('simulation_finish', simulationFinish);
        socket.on('simulation_data', receiveSimulationData);
        //socket.emit('subcribe_to_simulation', 6);
        //socket.emit('run_simulation', 'ac.json');
        socket.on('scenario_file', receiveSimulationScenarios);
        socket.emit('get_scenario_file');

        //socket.on('simulation_runs', receiveSimulationRuns);

        socket.on('simulation_runs', receiveSimulationRuns);
        socket.emit('get_simulation_runs');

        socket.on('remove_sim_run_success', removeSimulationRunSuccess);
        socket.on('remove_sim_run_error', removeSimulationRunError);
        ctrl.removeSimulationRun = removeSimulationRun;


        ctrl.initialized = true;

        //init();

        ////
        //

        function receiveSimulationData(data){
            console.log('receiveData', data);
            for(let item of data){
                ctrl.simulation_data.push(item);
                ctrl.sim_data.addLine(item);
            }
            console.log('sim data', ctrl.sim_data);
            //ctrl.response_data.push(data);
        }

        function receiveSimulationScenarios(data){
            console.log('scenarios...', data);
            for (const sr of data) {
                ctrl.scenario_list.push(sr);
            }
        }

        function receiveError(err){
            console.log('receiveError', err);
        }

        function simulationFinish(data){
            console.log('simulationFinish', data);
        }

        function receiveSimulationRuns(data){
            console.log('received simulation runs...', data, typeof data);
            if (Array.isArray(data)){
                for (const sr of data) {
                    ctrl.sim_run_list.push(sr);
                }
            }
            else {
                ctrl.sim_run_list.splice(0, 0, data);
                ctrl.selected_run = data;
                ctrl.sim_run = data;
            }
        }

        function tagIsSelected(device, tag){
            // is the device/tag selected?
            // if so there is a TagView object with device & tag properties
            return ctrl.selected_tag_views.findIndex((item) => item.device == device && item.tag == tag) >= 0
        }

        function toggleTagView(device, tag){
            let index = ctrl.selected_tag_views.findIndex((item) => item.device == device && item.tag == tag);
            if (index == -1) {
                ctrl.selected_tag_views.push(new TagView(device, tag));
            }
            else {
                ctrl.selected_tag_views.splice(index, 1);
            }
        }

        function init() {
            console.log('sinit');
            //api.simulation_run.get().then(
                //function(results){
                    //ctrl.sim_run_list = results;
                    //ctrl.grid_options_run.data = results;
                    //ctrl.initialized = true;
                    //console.log("homeController test success", results);
                //},
                //function(err){
                    //console.log('homeController Error', err);
                //}
            //)
        }

        function showNav(){
            ctrl.side_nav_is_open = !ctrl.side_nav_is_open;
        }

        function selectSimulationScenario(scenario){
            console.log('select scenario', scenario);
            ctrl.scenario = scenario;
        }

        function runScenario(scenario){
            /// run the selected scenario
            console.log('run_scenario', scenario);
            socket.emit('run_simulation', scenario.content);
            ctrl.is_running = true;
        }

        function selectSimulationRun(sim_run){
            ctrl.sim_run = sim_run;
            console.log('select simulation run', sim_run);
            //api.simulation_run_data.get(sim_run.id).then(
                //function(results){
                    //console.log('results', results);
                    //ctrl.sim_info = results;
                //},
                //function(err){
                    //console.error('error', err);
                //}
            //);
        }

        function removeSimulationRun(sim_run){
            // remove simulation runs from the database
            console.log('remove simulation run', sim_run);
            socket.emit('remove_sim_run', sim_run);
        }

        function removeSimulationRunSuccess(sim_run){
            console.log('successfully removed run ', sim_run);
            if (sim_run == 'all'){
                ctrl.sim_run_list.splice(0, ctrl.sim_run_list.length);
            }
            else {
                let index = ctrl.sim_run_list.findIndex((d) => d.id == sim_run);
                if (index >= 0) {
                    ctrl.sim_run_list.splice(index, 1);
                }
            }
        }

        function removeSimulationRunError(err){
            console.log('simulation run error', err);
        }


        //function getSimulationData(sim_run){
            //ctrl.sim_run = sim_run;
            //api.simulation_run_all_data.get(sim_run.id).then(
                //function(results){
                    //console.log('results', results);
                    ////ctrl.simulation_data = results;
                //},
                //function(err){
                    //console.error('error', err);
                //}
            //);
        //}

        function selectDeviceTag(device, tag) {
            // select a tag for a device to show the results
            api.simulation_run_tag.get(ctrl.sim_run.id, device.device, tag.tag).then(
                function(results){
                    console.log('get device tag data ', results);

                },
                function(err){
                    console.log('error', err);
                }
            )
        }

    }
})();

