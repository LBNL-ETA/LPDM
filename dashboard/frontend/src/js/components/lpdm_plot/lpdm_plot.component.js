 (function() {
     'use strict';
     angular
         .module('lpdmApp')
         .component('lpdmPlot', {
             templateUrl: 'js/components/lpdm_plot/lpdm_plot.template.html',
             controller: lpdmPlotController,
             bindings: {
                 plot_data: "=plotData"
             }
         });

     lpdmPlotController.$inject = ['$scope', '$element', '$attrs', '$timeout', 'moment'];
     function lpdmPlotController($scope, $element, $attrs, $timeout, moment){
         var ctrl = this;
         var container = $element.find("div.plot_container");

         // watch the data source for changes
         $scope.$watch(
             function() {
                 return ctrl.plot_data;
             },
             function() {
                 if (ctrl.plot_data) {
                     $timeout(
                         function() {
                             console.log('create the plot', ctrl.plot_data);
                             generatePlot(ctrl.plot_data);
                         },
                         500
                     );
                 }
             },
             true
         );

         ////

         function generatePlot(plot_data) {
             var series = [];
             var x = [];
             var y = [];

             // remove the existing plot
             container.empty();
             Plotly.purge(container[0]);

             plot_data.tag.runs.forEach((run) => {
                 let new_series = {
                     name: `run: ${ run.run_id }`,
                     x: [],
                     y: [],
                     mode: 'lines+markers',
                     line: {shape: 'hv'},
                     type: 'scatter'
                 };
                 run.values.forEach((run_value) => {
                     new_series.y.push(run_value.value);
                     new_series.x.push(moment.moment.utc(run_value.sim_time.time_value * 1000).format('YYYY-MM-DD HH:mm:ss'));
                     //console.log(moment.moment.utc(run_value.sim_time.time_value * 1000).format('YYYY-MM-DD HH:mm:ss'));
                 })
                 series.push(new_series);
             })

             //plot_data.forEach(function(item){
                 //x.push(moment.moment.utc(item.date).format("YYYY-MM-DD HH:mm:ss"));
                 //y_power.push(item.energy)
             //});

             //var series = [];
             //series.push({
                 //x: x,
                 //y: y_power,
                 //name: 'Energy',
                 //type: 'line',
                 //color: '#d62c1a'
             //});

             //var shapes = [
                //{
                    //type: 'rect',
                    //xref: 'x',
                    //yref: 'paper',
                    //x0: '2015-04-23',
                    //y0: 0,
                    //x1: '2015-04-25',
                    //y1: 1,
                    //fillcolor:'#eb6d60',
                    //opacity: 0.3,
                    //line: {
                        //width: 3,
                        //color: '#eb6d60'
                    //},
                    //layer: 'below'
                //}];
            //var shapes = getShapes(agg_faults);

            var layout = {
                margin: {
                    t: 0
                },
                xaxis: {
                    tickformat: "Day# %j: %H:%M:%S",
                    color: "white"
                },
                yaxis: {
                    //title: 'Energy (kWh)',
                    color: 'white',
                    //showline: false,
                    //zeroline: false,
                    //rangemode: 'nonnegative',
                    autorange: true
                },
                showlegend: true,
                paper_bgcolor: "#424242",
                plot_bgcolor: "#424242",
                font: {
                    color: "white"
                }
                //legend: {
                    //orientation: 'h',
                //},
                //shapes: shapes
            };

            Plotly.plot(container[0] , series, layout, {displaylogo: false});
        }

        function getShapes(agg_faults) {
            var shapes = [];
            if (angular.isArray(agg_faults)) {
                agg_faults.forEach(function(agg){
                    if (angular.isArray(agg.faults) && agg.faults.length) {
                        agg.faults.forEach(function(item){
                            shapes.push({
                                type: 'rect',
                                xref: 'x',
                                yref: 'paper',
                                x0: item.start_date,
                                y0: 0,
                                x1: item.end_date,
                                y1: 1,
                                fillcolor:'#eb6d60',
                                opacity: 0.3,
                                line: {
                                    width: 3,
                                    color: '#eb6d60'
                                },
                                layer: 'below'
                            });
                        });
                    }
                });
            }
            return shapes;
        }
    }
})();
