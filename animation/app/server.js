// server.js
// where your node app starts

// init project
const express = require('express')
const bodyParser = require('body-parser')
var fs = require('fs');
const fileUpload = require('express-fileupload');
const app = express()

// we've started you off with Express, 
// but feel free to use whatever libs or frameworks you'd like through `package.json`.

// http://expressjs.com/en/starter/static-files.html
app.use(express.static('public'))
app.use(bodyParser.json());
app.use(fileUpload());

// http://expressjs.com/en/starter/basic-routing.html
app.get("/", (request, response) => {
  response.sendFile(__dirname + '/views/index.html')
})

function loadSystemList() {
  if(fs.existsSync(".data/systemList.json")) {
    var systemList = fs.readFileSync(".data/systemList.json");
    return JSON.parse(systemList)
  }else{
    return [];
  }
}

function saveSystemList(systemList) {
  fs.writeFileSync(".data/systemList.json", JSON.stringify(systemList));
}

function findMaxId(list){
  var counter = 0;
  list.forEach(function(item) {
    if(item.id > counter){
      counter = item.id;
    }
  })
  return counter;
}

function findMaxSimId(list){
  var counter = 0;
  list.forEach(function(item) {
    var itemId = parseInt(item.id.split("\.")[1], 10);
    console.log(itemId);
    if(itemId > counter){
      counter = itemId;
      console.log(counter);
    }             
  })
  return counter;
}

function loadSystem(systemId) {
  if(fs.existsSync(".data/system" + systemId + ".json")) {
    var system = fs.readFileSync(".data/system" + systemId + ".json");
    return JSON.parse(system)
  }else{
    return null;
  }
}


function saveSystem(system) {
  fs.writeFileSync(".data/system" + system.id + ".json", JSON.stringify(system));
}

function deleteSystem(systemId) {
  var systemList = loadSystemList();
  systemList = systemList.filter(function(systemInfo) {
    return systemInfo.id != systemId;
  });
  saveSystemList(systemList);
}

function createSystem(name, config){
  var system = {};
  var systemList = loadSystemList();
  var maxId = findMaxId(systemList);
  system.id = maxId + 1;
  system.name = name;
  system.config = config;
  system.layout = {
    links: {}
  };
  saveSystem(system);
  systemList.push({id: system.id, name: system.name});
  saveSystemList(systemList);
  return system;
}

function loadSimulation(simId) {
  if(fs.existsSync(".data/sim" + simId + ".json")) {
    var simulation = fs.readFileSync(".data/sim" + simId + ".json");
    return JSON.parse(simulation)
  }else{
    return null;
  }
}


function saveSimulation(sim) {
  fs.writeFileSync(".data/sim" + sim.id + ".json", JSON.stringify(sim));
}

function deleteSimulation(simId) {
  var simulation = loadSimulation(simId);
  var systemId = simulation.systemId;
  var system = loadSystem(systemId);
  console.log(simId, systemId, simulation);
  system.simList = system.simList.filter(function(simInfo) {
    return simInfo.id != simId;
  });
  saveSystem(system);
}

function createSimulation(systemId, name, events){
  var system = loadSystem(systemId);
  var simulation = {};
  if(!system.simList){
    system.simList = [];
  }
  var maxId = findMaxSimId(system.simList);
  simulation.id = systemId + "." + (maxId + 1);
  simulation.systemId = systemId;
  simulation.name = name;
  simulation.events = events.filter(function(event) {
    return event.length > 0;
  });
  system.simList.push({id: simulation.id, name: simulation.name});
  saveSystem(system);
  saveSimulation(simulation);
  return simulation;
}


//
// API methods for reading/writing data
// 

app.get("/api/systemList", (request, response) => {
  var systemList = loadSystemList();
  response.json(systemList);
})

app.get("/api/system", (request, response) => {
  var id = request.query.id;
  var system = loadSystem(id);
  if(system != null) {
    console.log("GET /system => " + JSON.stringify(system)); 
    response.json(system);
  }else{
    response.sendStatus(404)
    response.end()
  }
})

app.put("/api/system", (request, response) => {
  var system = request.body;
  saveSystem(system);
  console.log("POST /system => " + JSON.stringify(system));
  response.sendStatus(200)
  response.end()
})

app.delete("/api/system", (request, response) => {
  var id = request.query.id;
  deleteSystem(id);
  console.log("deleted system  id:" + id);
  response.sendStatus(200);
  response.end();
})

app.get("/api/simulation", (request, response) => {
  var id = request.query.id;
  var simulation = loadSimulation(id);
  if(simulation != null) {
    console.log("GET /simulation => " + JSON.stringify(simulation)); 
    response.json(simulation);
  }else{
    response.sendStatus(404)
    response.end()
  }
})

app.put("/api/simulation", (request, response) => {
  var simulation = request.body;
  saveSimulation(simulation);
  console.log("POST /simulation => " + JSON.stringify(simulation));
  response.sendStatus(200)
  response.end()
})

app.delete("/api/simulation", (request, response) => {
  var id = request.query.id;
  deleteSimulation(id);
  console.log("deleted simulation  id:" + id);
  response.sendStatus(200);
  response.end();
})

app.get("/system", (request, response) => {
  response.sendFile(__dirname + '/views/system.html')
})

app.post('/system', (request, response) => {
  console.log("Uploading...");
  
  if (Object.keys(request.files).length == 0) {
    return response.status(400).send('No files were uploaded.');
  }
  if (request.query.name == ""){
    return response.status(400).send("Please choose a name.");
  }

  // The name of the input field (i.e. "sampleFile") is used to retrieve the uploaded file
  var configFile = request.files.configFile.data.toString();
  var system = createSystem(request.body.name, JSON.parse(configFile));
  console.log(system, request.body.name);
  
  response.redirect('/system?id=' + system.id);

});

app.post('/simulation', (request, response) => {
  console.log("Uploading...");
  
  if (Object.keys(request.files).length == 0) {
    return response.status(400).send('No files were uploaded.');
  }
  if (request.query.name == ""){
    return response.status(400).send("Please choose a name.");
  }

  // The name of the input field (i.e. "sampleFile") is used to retrieve the uploaded file
  var systemId = request.body.systemId;
  var logFile = request.files.logFile.data.toString();
  var simulation = createSimulation(systemId, request.body.name, logFile.split(/\r?\n/));
  console.log(simulation, request.body.name);
  
  response.redirect('/system?id=' + systemId + "&simId=" + simulation.id);

});

// listen for requests :)
const listener = app.listen(process.env.PORT, () => {
  console.log(`Your app is listening on port ${listener.address().port}`)
})