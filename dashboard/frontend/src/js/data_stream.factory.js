(function() {
    'use strict';
    angular
        .module("lpdmApp")
        .factory("data_stream", dataStream);

    function dataStream($q, $http, socket){

        return {
            subscribeToSimulationRun: subscribeToSimulationRun
        };

        ////

        function subscribeToSimulationRun(id, fnData, fnError){
            console.log('emit...');
            socket.on('simulation_data', fnData);
            socket.emit('subscribe_to_simulation', id);
        }

        function getScenario() {
            var deferred = $q.defer();
            $http.get("/lpdm/api/scenario/").then(
                function(results){
                    console.log('results success', results);
                    if (results && results.data && results.data.scenarios){
                        deferred.resolve(results.data.scenarios);
                    }
                    else {
                        deferred.reject();
                    }
                },
                function(err) {
                    console.log('results error', err);
                    deferred.reject(err);
                }
            )
            return deferred.promise;
        }

        function getSimulationRun() {
            var deferred = $q.defer();
            $http.get("api/simulation/").then(
                function(results){
                    console.log('results success', results);
                    if (results && results.data){
                        deferred.resolve(results.data);
                    }
                    else {
                        deferred.reject();
                    }
                },
                function(err) {
                    console.log('results error', err);
                    deferred.reject(err);
                }
            )
            return deferred.promise;
        }

        function getSimulationRunData(id) {
            var deferred = $q.defer();
            $http.get(`api/simulation_data/${ id }/device`).then(
                function(results){
                    console.log('results success', results);
                    if (results && results.data){
                        deferred.resolve(results.data);
                    }
                    else {
                        deferred.reject();
                    }
                },
                function(err) {
                    console.log('results error', err);
                    deferred.reject(err);
                }
            )
            return deferred.promise;
        }

        function getSimulationRunAllData(id) {
            var deferred = $q.defer();
            $http.get(`api/simulation_data/${ id }`).then(
                function(results){
                    console.log('results success', results);
                    if (results && results.data){
                        deferred.resolve(results.data);
                    }
                    else {
                        deferred.reject();
                    }
                },
                function(err) {
                    console.log('results error', err);
                    deferred.reject(err);
                }
            )
            return deferred.promise;
        }

        function getSimulationTagData(id, device_id, tag) {
            var deferred = $q.defer();
            $http.get(`api/simulation_data/${ id }/${ device_id }/${ tag }`).then(
                function(results){
                    console.log('results success', results);
                    if (results && results.data){
                        deferred.resolve(results.data);
                    }
                    else {
                        deferred.reject();
                    }
                },
                function(err) {
                    console.log('results error', err);
                    deferred.reject(err);
                }
            )
            return deferred.promise;
        }
    }
})();
