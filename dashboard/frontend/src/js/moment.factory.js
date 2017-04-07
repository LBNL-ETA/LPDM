(function() {
    'use strict';
    angular
    .module('lpdmApp')
    .factory('moment', moment);

    moment.$inject = ['$window'];
    function moment($window) {
        return {
            moment: $window.moment
        };
    }
})();

