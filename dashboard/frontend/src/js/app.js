(function() {
    'use strict';
    angular
        .module("lpdmApp", [
            'ui.router',
            'ngMaterial',
            'ui.grid'
        ])
        .config(config);

    function config($urlRouterProvider, $stateProvider, $httpProvider, $interpolateProvider, $mdThemingProvider){
        //$interpolateProvider.startSymbol('{[{');
        //$interpolateProvider.endSymbol('}]}');

        $mdThemingProvider.theme('default')
            .dark();

        //$mdThemingProvider.theme('docs-dark', 'default')
            //.primaryPalette('yellow')
            //.dark();
        //$mdThemingProvider
        //.theme('default')
            //.primaryPalette('blue')
            //.accentPalette('teal')
            //.warnPalette('red')
            //.backgroundPalette('grey');

        $urlRouterProvider.otherwise("home");

        $stateProvider
            .state("home", {
                templateUrl: "views/home/home.template.html",
                url: "/home",
                controller: 'homeController',
                controllerAs: 'ctrl'
            })
            .state("scenarios", {
                templateUrl: "views/scenarios/scenarios.template.html",
                url: "/scenarios",
                controller: 'scenariosController',
                controllerAs: 'ctrl'
            })
            ;
    }

})();
