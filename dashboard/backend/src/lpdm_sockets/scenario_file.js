var path = require('path');
var fs = require('fs');
var glob = require("glob")
var pool = require('../database');

module.exports = (socket) => {
    socket.on('get_scenario_file', () => getScenarioFile(socket));
}

function getScenarioFile(socket){
        // return the list of scenario files and their contents as json
     console.log('get scenario files from /simulation/scenarios')
     let scenario_folder = '/simulation/scenarios';
     fs.readdir(scenario_folder, (err, files) => {
         console.log('readdir');
         console.log(err);
         console.log(files);
         files.forEach(file => {
                 console.log(file);
         });
     });
     glob("/simulation/scenarios/*.json", {}, function (er, files) {
         console.log('found scenario files');
         console.log(er);
         console.log(files);
         scenarios = [];
         for (const fname of files) {
             console.log(`read file ${ fname }`);
             try{
                 var obj = JSON.parse(fs.readFileSync(fname, 'utf8'));
             }
             catch(err) {
                 obj = null;
             }
             scenarios.push({file_name: path.basename(fname), content: obj});
         }
         socket.emit('scenario_file', scenarios);
     });
}
