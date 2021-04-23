var w = window.innerWidth * .75;
var h = window.innerHeight * .75;
var system = {};
var simulation = null;
var nextEventIndex = 0;
var currentSecond = 0;
var lastSecond = 0;
var timeStepDuration = 1000;
var secsPerTimeStep = 60;
var running = false;
var graph;
var paper;
var devices = {};
var currTime = {
  seconds: 0,
  minutes: 0,
  hours: 0,
  days: 0
};
var reverse = 1;
var displayOn = true;
var simEnd;
var wasRunning;

var deviceInfo = {
  air_conditioner: {
    imageUrl: "https://cdn.glitch.com/5e4ea8dc-99b1-4be8-afdf-1fb3722e6bc4%2Fair_conditioner.png?1550353431169",
    defaultState: {compressor: 0, setPoint: 0}
  },
  light: {
    imageUrl: "https://cdn.glitch.com/5e4ea8dc-99b1-4be8-afdf-1fb3722e6bc4%2Flight.png?1550353425519",
    defaultState: {brightness: 0}
  },
  fixed_consumption: {
    defaultState: {}
  },
  pv: {
    imageUrl: "https://cdn.glitch.com/5e4ea8dc-99b1-4be8-afdf-1fb3722e6bc4%2Fimage.png?1547744211793"
  },
  utm: {
    imageUrl: "https://cdn.glitch.com/5e4ea8dc-99b1-4be8-afdf-1fb3722e6bc4%2Futility_meter.png?1550352964675"
  }
} 

$(function() {
  const urlParams = new URLSearchParams(window.location.search);
  const systemId = urlParams.get('id');
  const simId = urlParams.get('simId');
  
  
  $.get("/api/system?id=" + systemId)
    .done(function(_system) {
      system = _system;
      displaySystem();
      console.log(_system);
      $("#systemName").html(system.name);
      system.simList.forEach(function(item) {
        var itemId = item.id.replace("\.", "");
        $("#simulationList").append('<li id="listItem' + itemId +'" class="simListItem"><a href="/system?id=' + systemId + '&simId='+ item.id + '"><span class="tab">' + 
        item.name + '</span></a> <a id="delete' + itemId + '" href="#" class="deleteLink"><i class="fas fa-trash-alt"></i></a></li>');
        $("#delete" + itemId).click(function() {
          console.log("deleting" + itemId);
          $.ajax({ 
            url: '/api/simulation?id=' + item.id, 
            type: 'DELETE',
            contentType: 'application/json', 
            success: function() {
              console.log("deleted simulation");
              $("#listItem" + itemId).remove();
            }
          })
        })
      })
    
      if(simId){
        $.get("/api/simulation?id=" + simId)
          .done(function(_sim) {
            simulation = _sim;
            displayTimeline();
            resetSimulation();
            $("#simulationName").html(simulation.name);
            simEnd = simulation.events.length;
          })
      }

  })
  
  $("#systemSave").click(function() {
    delete system.layout.links;
    Object.keys(system.layout).forEach(function(device_id){
      console.log("trying to record layout for " + device_id);
      system.layout[device_id].x = devices[device_id].node.attributes.position.x;
      system.layout[device_id].y = devices[device_id].node.attributes.position.y;
      if(!system.layout[device_id].links){
        system.layout[device_id].links = {};
      }
      Object.keys(devices[device_id].links).forEach(function(targetDeviceId) {
        if(!system.layout[device_id].links[targetDeviceId]){
          system.layout[device_id].links[targetDeviceId] = {};
        }
        system.layout[device_id].links[targetDeviceId].vertices = devices[device_id].links[targetDeviceId].link.vertices();
      })
    });
    console.log(system);
    $.ajax({ 
      url: '/api/system', 
      type: 'PUT',
      contentType: 'application/json', 
      data: JSON.stringify(system),
      success: function() {
        console.log("saved system");
        $("#message").html('Saved').show().delay(3200).fadeOut(300);
      }
    })
  })
  $("#runSimulation").click(function() {
    running = true;
    run();
  })
  $("#pauseSimulation").click(function() {
    refreshAll();
    running = false;
  })
  $("#stopSimulation").click(function() {
    running = false;
    resetSimulation();
  })
  $("#reverseTime").click(function(){
    reverseTime();
  })
  $("#uploadSystemId").val(systemId);
  
  $( ".radioInput" ).checkboxradio();
  $( "#radioFieldset" ).controlgroup();
  
  $(".radioInput").click(function(){
    var radioValue = $("input[name='radio-1']:checked").val();
    secsPerTimeStep = radioValue;
  });
  
  var handle = $( "custom-handle" );
  $( ".slider" ).slider({
    create: function() {
      handle.text( $( this ).slider( "value" ) );
    },
    slide: function( event, ui ) {
      handle.text( ui.value );
      timeStepDuration = 1000 - (ui.value * 10);
    }
  });
  $( "#master" ).slider({
      value: 60,
      orientation: "horizontal",
      range: "min",
      animate: true
    });
 
});

let canvasElem = document.querySelector("#scrubber"); 
          
canvasElem.addEventListener("mousedown", function(e) { 
  getMousePosition(canvasElem, e); 
}); 

graph = new joint.dia.Graph;

paper = new joint.dia.Paper({
  el: document.getElementById('systemDisplay'),
  model: graph,
  width: w,
  height: h,
  gridSize: 1,
  background: {
      color: 'rgba(0, 255, 0, 0.3)'
  },
});

/*paper.options.defaultRouter = {
  name: 'manhattan',
  args: {
    padding: 10,
    startDirections: ['bottom'],
    endDirections: ['top']
  }
};*/

graph.on('change:position', function(cell) {

    // has an obstacle been moved? Then reroute the link.
    //if (obstacles.indexOf(cell) > -1) paper.findViewByModel(link).update();
});

paper.on('link:mouseenter', function(linkView) {
    var tools = new joint.dia.ToolsView({
        tools: [new joint.linkTools.Vertices()]
    });
    linkView.addTools(tools);
});

paper.on('link:mouseleave', function(linkView) {
    linkView.removeTools();
});

function reverseTime(){
  reverse = reverse * -1;
  console.log("time reversed");
}

function advanceTime(timeStep){
  currentSecond += timeStep;
  for(var i = 0; i < timeStep; i++){
    currTime.seconds++;
    if(currTime.seconds == 60){
      currTime.minutes++;
      currTime.seconds = 0;
    }
    if(currTime.minutes == 60){
      currTime.hours++;
      currTime.minutes = 0;
    }
    if(currTime.hours == 24){
      currTime.days++;
      currTime.hours = 0;
    }
  }
}

function run(){
  var timeoutSet = false;
  while(running && nextEventIndex < simEnd){
    //if()
    $("#time").html(currentSecond);
    $("#clock").html(currTime.days + " " + currTime.hours.toString().padStart(2, "0") + ":" + currTime.minutes.toString().padStart(2, "0") + ":" + currTime.seconds.toString().padStart(2, "0"));
    displayScrubberPosition();
    var delay;
    var skipRate;
    var nextEvent = parseEvent(simulation.events[nextEventIndex]);
    if(nextEvent != null && nextEvent.second == currentSecond){
      $("#eventLog").prepend(nextEvent.timeStamp.day + ", " + nextEvent.timeStamp.time + ", " + nextEvent.second + ", " + nextEvent.deviceId + ", " + nextEvent.eventType + ", " +  nextEvent.action + "<br>");
      displayEvent(nextEvent);
      nextEventIndex++;
      delay = 0;
    }else{
      var timeStep = Math.min(secsPerTimeStep, nextEvent.second - currentSecond);
      advanceTime(timeStep);
      delay = timeStepDuration;
    }
    if(displayOn || nextEventIndex % 100 == 0){
      timeoutSet = true;
      setTimeout(run, delay);
      break;
    }
  }
  if(displayOn == false && !timeoutSet){
    if(!wasRunning){
      running = false;
      wasRunning = true;
    }
    displayOn = true;
    simEnd = simulation.events.length;
    setTimeout(run, delay);
  }
}

function resetSimulation(){
  var firstEvent = parseEvent(simulation.events[0]);
  var lastEvent = getLastEvent();
  console.log("lastEvent", lastEvent);
  currentSecond = firstEvent.second;
  lastSecond = lastEvent.second;
  nextEventIndex = 0;
  $("#time").html(currentSecond);
  currTime.seconds = 0;
  currTime.minutes = 0;
  currTime.hours = 0;
  currTime.days = 0;
  $("#clock").html(currTime.days + " " + currTime.hours.toString().padStart(2, "0") + ":" + currTime.minutes.toString().padStart(2, "0") + ":" + currTime.seconds.toString().padStart(2, "0"));
  displaySystem();
  displayScrubberPosition();
  $("#eventLog").html("");
}

function getBaseLog(x, y) {
  return Math.log(y) / Math.log(x);
}

function getLastEvent(){
  var eventSecond = 0;
  var lastEvent;
  var num = 0;
  while(eventSecond == 0 && num != simulation.events.length){
    num++;
    lastEvent = parseEvent(simulation.events[simulation.events.length-num]);
    eventSecond = lastEvent.second;
  } 
  return lastEvent;
  
}

function parseEvent(eventString) {
  var comps = eventString.split(";");
  if(comps.length >= 5){
    var event = {
      timeStamp: {
        day: comps[0].trim().split(" ")[0],
        time: comps[0].trim().split(" ")[1]
      },
      second: parseInt(comps[1].trim()),
      deviceId: comps[2].trim(),
      eventType: comps[3].trim(),
      value: comps[4].trim(),
      action: comps[5].trim()
    }
    return event;
  }else{
    var event = {
      timeStamp: {
        day: 0,
        time: 0
      },
      second: 0,
      deviceId: "",
      eventType: "",
      value: 0,
      action: ""
    }
    return event;
  }
}

function lastElement(arr) {
  return arr[arr.length - 1];
}

function refreshDevice(device_id) {
  var device = devices[device_id];
  var deviceType = device.config.device_type;
  if(deviceType == "grid_controller"){
    device.node.attr({
      label:{
        text: device_id + " \nsoc: " + device.state.soc.toFixed(3) + " \nprice: " + device.state.price.toFixed(3),
        fill: 'white'
      }
    })
  }else if(deviceType == "eud"){
    if(device.config.eud_type == "air_conditioner"){
      device.node.attr({
        label:{
          text: device_id + " \ncomp: " + device.state.compressor + " \nset: " + device.state.setPoint.toFixed(3),
          fill: 'white'
        }
      })
  
    }else if(device.config.eud_type == "light"){
      device.node.attr({
        label:{
          text: device_id + "\nbright: " + device.state.brightness.toFixed(3),
          fill: 'white'
        }
      })
    }
  }
}

function refreshLink(sourceDeviceId, targetDeviceId){
  var widthClasses = ["linkPower2", "linkPower3", "linkPower4", "linkPower5", "linkPower6"];
  var link = devices[targetDeviceId].links[sourceDeviceId].link;
  var linkView = paper.findViewByModel(link);
  var label;
  var linkState = devices[targetDeviceId].links[sourceDeviceId].state;
  if(linkState.power != 0){
    var linkClass;
    if(devices[targetDeviceId].config.device_type == "utility_meter"){
      linkClass = "linkWithPowerUp";
    }else{
      linkClass = "linkWithPowerDown";
    }
    $(linkView.selectors.line).addClass(linkClass);
    widthClasses.forEach(function(e) {
       $(linkView.selectors.line).removeClass(e);
    });
    $(linkView.selectors.line).addClass(widthClasses[getLineWidth(linkState.power) - 2]);
    label = Math.abs(linkState.power) + "W";
  }else{
    label = "";
    $(linkView.selectors.line).removeClass("linkWithPowerDown");
    $(linkView.selectors.line).removeClass("linkWithPowerUp");
    widthClasses.forEach(function(e) {
       $(linkView.selectors.line).removeClass(e);
    });
  }
  link.label(0, {
      attrs: { text: { text: label}}
  })
  var requestLabel = (linkState.requestPower != 0)? Math.round(linkState.requestPower) + "W" : "";
  link.label(2, {
      attrs: { text: { text: requestLabel, fill:'Red'}},
      position: {
        distance: 1
      }
  });
  var allocateLabel = (linkState.allocatePower != 0)? Math.round(linkState.allocatePower) + "W" : "";
  link.label(3, {
      attrs: { text: { text: allocateLabel, fill: '#32CD32'}},
      position: {
        distance: .1
      }
  });
}

function refreshAll(){
  Object.keys(devices).forEach(function(device_id){
    let device = devices[device_id];
    Object.keys(device.links).forEach(function(targetDeviceId){
      refreshLink(device_id, targetDeviceId);
      
    });
    refreshDevice(device_id);
  });
}


function updateSOC(grid_controller_id, soc){
  devices[grid_controller_id].state.soc = soc;
  if(displayOn){
    refreshDevice(grid_controller_id);
  }
}

function updatePrice(device_id, price){
  devices[device_id].state.price = price;
  if(displayOn){
    refreshDevice(device_id);
  }
}
            
function updateDeviceStateValue(device_id, attribute, value){
  devices[device_id].state[attribute] = value;
  if(displayOn){
    refreshDevice(device_id);
  }
}

function updatePowerMsg(sourceDeviceId, targetDeviceId, power){
  devices[targetDeviceId].links[sourceDeviceId].state.power = power;
  if(displayOn){
    refreshLink(sourceDeviceId, targetDeviceId);
  }
}

function updateRequestStateValue(sourceDeviceId, targetDeviceId, power){
  devices[targetDeviceId].links[sourceDeviceId].state.requestPower = power;
  if(displayOn){
    refreshLink(sourceDeviceId, targetDeviceId);
  }
}

function updateAllocateStateValue(sourceDeviceId, targetDeviceId, power){
  devices[targetDeviceId].links[sourceDeviceId].state.allocatePower = power;
  if(displayOn){
    refreshLink(sourceDeviceId, targetDeviceId);
  }
}

/*function updatePriceMessage(sourceDeviceId, targetDeviceId, power){
  
}*/

function findGridControllerId(device_id){
  var foundGC = system.config.devices.grid_controllers.find(function(gc) {
    return gc.connected_devices.includes(device_id);
  })
  if(foundGC != null){
    return foundGC.device_id;
  }else{
    return null;
  }
}

function displayEvent(event){
  switch(event.eventType) {
    case "power_msg":
    case "power_out":
      displayPowerMsg(event);
      break;
    case "battery_soc":
      displaySOCChange(event);
      break;
    case "price":
      displayPriceChange(event);
      break;
    case "price message":
    case "price_msg_in":
    case "price_msg_out":
      displayPriceMsg(event);
      break;
    case "brightness":
      displayBrightnessChange(event);
      break;
    case "set_point":
      displaySetPointChange(event);
      break;
    case "compressor_on_off":
      displayCompressorChange(event);
      break;
    case "request_out":
      displayRequestChange(event);
      break;
    case "allocate_msg":
      displayAllocateChange(event);
      break;
  }
}

function getLineWidth(power){
  return Math.min(Math.round(getBaseLog(4.2, Math.abs(power))), 6);
}

//1 10:10:00; 123000; pv_1; power_out; -1440.0; POWER to gc_1
//1 10:10:02; 123002; utm_1; power_msg_in; 60.0; POWER message from gc_1
//1 11:00:00; 126000; pv_1; power_msg; -1692.0; POWER to gc_1
function displayPowerMsg(event) {
  var power = Math.round(parseFloat(event.value));
  var powerToDeviceId = event.action.split(" ")[2];
  var sourceDeviceId, targetDeviceId;
  if(power < 0){
    sourceDeviceId = event.deviceId;
    targetDeviceId = powerToDeviceId;
  }else{
    sourceDeviceId = powerToDeviceId;
    targetDeviceId = event.deviceId;
  }
  //console.log("POWER, source: " + sourceDeviceId + ", target: " + targetDeviceId);
  updatePowerMsg(sourceDeviceId, targetDeviceId, power);
}

//0 00:15:00; 900; battery_1; soc; 0.7508333333333332; current soc
function displaySOCChange(event){
  updateSOC(event.deviceId, Number((parseFloat(event.value))));
}


//0 01:00:00; 3600; gc_1; price; 0.1; price changed to 0.1
//0, 11:00:02, 39602, eud_1, price, ignored request message from gc_1
function displayPriceChange(event) {
  var price = parseFloat(event.value);
  if(price != NaN){
    var deviceId = event.deviceId;
    updatePrice(deviceId, price);
  }
}

//0 00:00:00; 0; eud_4; brightness; 0.0; brightness changed to 0.0
function displayBrightnessChange(event){
  var brightness = parseFloat(event.value);
  if(brightness != NaN){
    var deviceId = event.deviceId;
    updateDeviceStateValue(deviceId, "brightness", brightness);
  }
}
//0 00:00:00; 0; eud_2; set_point; 17.0; setpoint changed to 17.0
function displaySetPointChange(event){
  var setPoint = parseFloat(event.value);
  if(setPoint != NaN){
    var deviceId = event.deviceId;
    updateDeviceStateValue(deviceId, "setPoint", setPoint);
  }
}
//0 00:00:02; 2; eud_1; compressor_on_off; 1; compressor_on
function displayCompressorChange(event){
  var compressor = event.value;
  var deviceId = event.deviceId;
  updateDeviceStateValue(deviceId, "compressor", compressor);
}

//0 00:00:00; 0; utm_1; price message; sell 0.1, buy 0; price msg to gc_1
//0 00:00:01; 1; gc_1; price_msg_in; 0.1; PRICE message from utm_1
//0 11:00:01; 39601; gc_1; price_msg_out; 0.05; PRICE to utm_1
function displayPriceMsg(event) {
  var source;
  var target;
  var price;
  if(event.eventType == "price_msg_in"){
    source = lastElement(event.action.split(" "));
    target = event.deviceId;
  }else if(event.eventType == "price_msg_out"){
    target = lastElement(event.action.split(" "));
    source = event.deviceId;
  }else{
    return;
  }
  price = event.value;
  if(displayOn){
    animatePriceMsg(source, target, price)
  };
  
}

//0 00:00:00; 0; eud_2; request_out; 500.0; REQUEST to gc_1
function displayRequestChange(event){
  var power = event.value;
  var source = event.deviceId;
  var target = event.action.split(" ")[2];
  updateRequestStateValue(source, target, power);
}

function displayAllocateChange(event){
  var power = event.value;
  var source = event.deviceId;
  var target = event.action.split(" ")[2]; 
  updateAllocateStateValue(source, target, power);
}

function displayTimeline(){
  var eventIndex = 0;
  var lastEvent = getLastEvent();
  var lastHour = parseInt(lastEvent.second/3600);
  var lineWidth = parseInt(1000/lastHour);
  var currEvent;
  var currHour;
  var difference = 0;
  var powerEventsPerHour = [];
  var priceEventsPerHour = [];
  for(var i = 0; i < lastHour; i++){
    powerEventsPerHour[i] = 0;
    priceEventsPerHour[i] = 0;
  }
  while(eventIndex != simulation.events.length){
    currEvent = parseEvent(simulation.events[eventIndex]);
    currHour = parseInt(currEvent.second/3600);
    if(currEvent.eventType == 'power_msg' || currEvent.eventType == 'power_out'){
      powerEventsPerHour[currHour]++;
    }else if(currEvent.eventType == 'price_msg_in' || currEvent.eventType == 'price_msg_out' || currEvent.eventType == 'price message'){
      priceEventsPerHour[currHour]++;
    }
    eventIndex++;
  }

  var maxPowerEvents = Math.max.apply(null, powerEventsPerHour);
  var maxPriceEvents = Math.max.apply(null, priceEventsPerHour)
  var powerWidths = [];
  var priceWidths = [];
  for(var l = 0; l < lastHour; l++){
    powerWidths[l] = parseInt(lineWidth * (powerEventsPerHour[l]/maxPowerEvents));
    priceWidths[l] = parseInt(lineWidth * (priceEventsPerHour[l]/maxPriceEvents));
  }

  var canvas = document.getElementById('eventCanvas');
  if (canvas.getContext) {
    var ctx = canvas.getContext('2d');
    ctx.fillStyle = 'orange';
    for(var k = 0; k < powerWidths.length; k++){
      ctx.fillRect(k*lineWidth, 0, powerWidths[k], 550)
    }
    ctx.fillStyle = 'green';
    for(var j = 0; j < priceWidths.length; j++){
      ctx.fillRect(j*lineWidth, 0, priceWidths[j], 550)
    }
  }
}


function animatePriceMsg(sourceId, targetId, price) {
  var link = devices[sourceId].links[targetId].link;
  var startPos = 0;
  var direction;
  if(link.getSourceElement().prop("deviceId") == sourceId){
    startPos = 0;
    direction = 1;
  }else{
    startPos = 100;
    direction = -1;
  }
  link.label(1, {
    attrs: { text: { text: price}}
  });
  advancePriceMsg(link, startPos, direction, price);
}

function advancePriceMsg(link, currPos, direction, price){
  //console.log("displaying price change of " + link);
  if(displayOn){
    if((direction == 1 && currPos != 100) || (direction == -1 && currPos != 0)){
      link.label(1, {
        position: {
          distance: currPos / 100
        }
      });
      setTimeout(function(){
        advancePriceMsg(link, currPos + (direction * 10), direction, price)
      }, 150);
    }else{
      link.label(1, {
        attrs: { text: { text: ""}},
        position: {
          distance: 0
        }
      });
    }
  }
}

function createLink(sourceId, targetId) {
  var sourceLayout = system.layout[sourceId];
  var link = new joint.shapes.standard.Link({
    source: devices[sourceId].node,
    target: devices[targetId].node,
    vertices: sourceLayout.links && sourceLayout.links[targetId] ? sourceLayout.links[targetId].vertices : null,
    attrs: {
      line: {
        targetMarker: {
            // the marker can be an arbitrary SVGElement
            'type': 'circle',
            'r': 0
        }
      }
    },
    labels: [{
      attrs: { text: { text: '' }},
      position: {
        offset: 0,
        distance: 0.5
      }
    },
    {
      attrs: { text: { text: '' }},
      position: {
        offset: 0,
        distance: 0
      }
    },
    {
      attrs: { text: { text: '' }},
      position: {
        offset: 0,
        distance: 0
      }
    },
    {
      attrs: { text: { text: '' }},
      position: {
        offset: 0,
        distance: 0
      }
    }]
  });
  var linkData = {
    state: {
      power: 0,
      allocatePower: 0,
      requestPower: 0
    },
    link: link
  };
  devices[targetId].links[sourceId] = linkData;
  devices[sourceId].links[targetId] = linkData;
  link.addTo(graph);
  return link;
} 

function displayScrubberPosition(){
  var position = (currentSecond/lastSecond) * 100;
  $("#locationBar").css("left", position + "%");
};

function getMousePosition(canvas, event) { 
  let canvasWidth = canvas.scrollWidth;
  let rect = canvas.getBoundingClientRect(); 
  let x = event.clientX - rect.left;
  let xPer = Math.round((x / canvasWidth) * 100);
  simEnd = Math.round((xPer/100) * simulation.events.length);
  if(simEnd < nextEventIndex){
    resetSimulation();
  }
  if(!running){
    wasRunning = false;
    running = true;
    run();
  }

  displayOn = false;
} 

function displaySystem(){
  devices = {};
  graph.clear();
  var xPos = 100;
  var yPos = 30;
  if(system.config.devices.pvs){
    system.config.devices.pvs.forEach(function(pv){
      var rect = new joint.shapes.standard.EmbeddedImage();
      if(system.layout[pv.device_id]){
        xPos = system.layout[pv.device_id].x;
        yPos = system.layout[pv.device_id].y;
      } else {
        system.layout[pv.device_id] = {};
        system.layout[pv.device_id].x = xPos;
        system.layout[pv.device_id].y = yPos;
      }
      rect.position(xPos, yPos);
      rect.resize(100, 50);
      rect.prop({deviceId: pv.device_id});
      rect.attr({
          body: {
              fill: 'green'
          },
          label: {
              text: pv.device_id,
              fill: 'white'
          },
          image: {
            xlinkHref: deviceInfo.pv.imageUrl
          }
      });
      rect.addTo(graph);
      pv.device_type = "pv";//Missing in example-config
      devices[pv.device_id] = {};
      devices[pv.device_id].config = pv;
      devices[pv.device_id].node = rect;
      devices[pv.device_id].links = {};
      devices[pv.device_id].state = {};
      devices[pv.device_id].rank = 0;
      xPos = xPos + 150;
    })
  }
  if(system.config.devices.utility_meters){
    system.config.devices.utility_meters.forEach(function(utm){
      var rect = new joint.shapes.standard.EmbeddedImage();
      if(system.layout[utm.device_id]){
        xPos = system.layout[utm.device_id].x;
        yPos = system.layout[utm.device_id].y;
      } else {
        system.layout[utm.device_id] = {};
        system.layout[utm.device_id].x = xPos;
        system.layout[utm.device_id].y = yPos;
      }
      rect.position(xPos, yPos);
      rect.resize(100, 50);
      rect.prop({deviceId: utm.device_id});
      rect.attr({
          body: {
              fill: 'blue'
          },
          label: {
              text: utm.device_id,
              fill: 'white'
          },
          image: {
            xlinkHref: deviceInfo.utm.imageUrl
          }
      });
      rect.addTo(graph);
      utm.device_type = "utility_meter";
      devices[utm.device_id] = {};
      devices[utm.device_id].config = utm;
      devices[utm.device_id].node = rect;
      devices[utm.device_id].links = {};
      devices[utm.device_id].state = {};
      devices[utm.device_id].rank = 0;
      xPos = xPos + 150;
    })
  }
  xPos = 100;
  yPos = 140;
  if(system.config.devices.grid_controllers){
    system.config.devices.grid_controllers.forEach(function(gc){
      var rect = new joint.shapes.standard.Rectangle();
      if(system.layout[gc.device_id]){
        xPos = system.layout[gc.device_id].x;
        yPos = system.layout[gc.device_id].y;
      } else {
        system.layout[gc.device_id] = {};
        system.layout[gc.device_id].x = xPos;
        system.layout[gc.device_id].y = yPos;
      }
      rect.position(xPos, yPos);
      rect.resize(100, 60);
      rect.prop({deviceId: gc.device_id});
      rect.attr({
        body: {
            fill: 'grey'
        },
        label: {
            text: gc.device_id,
            fill: 'white'
        }
      });
      rect.addTo(graph);
      gc.device_type = "grid_controller";
      devices[gc.device_id] = {};
      devices[gc.device_id].config = gc;
      devices[gc.device_id].node = rect;
      devices[gc.device_id].links = {};
      devices[gc.device_id].state = {soc: 0.000, price: 0.000};
      devices[gc.device_id].rank = 1;
      xPos = xPos + 150;
      refreshDevice(gc.device_id);
      //updateSOC(gc.device_id, gc.battery['starting soc']);
    })
  }
  xPos = 100;
  yPos = 250;
  if(system.config.devices.euds){
    system.config.devices.euds.forEach(function(eud){
      var rect = new joint.shapes.standard.EmbeddedImage();
      if(system.layout[eud.device_id]){
        xPos = system.layout[eud.device_id].x;
        yPos = system.layout[eud.device_id].y;
      } else {
        system.layout[eud.device_id] = {};
        system.layout[eud.device_id].x = xPos;
        system.layout[eud.device_id].y = yPos;
      }
      rect.position(xPos, yPos);
      rect.resize(150, 55)
      rect.prop({deviceId: eud.device_id});
      if(deviceInfo[eud.eud_type]){
        rect.attr('image/xlinkHref', deviceInfo[eud.eud_type].imageUrl);
      }
      rect.attr({
          body: {
              fill: 'orange'
          },
          label: {
              text: eud.device_id,
              fill: 'white'
          }
      });
      rect.addTo(graph);
      eud.device_type = "eud"
      devices[eud.device_id] = {};
      devices[eud.device_id].config = eud;
      devices[eud.device_id].node = rect;
      devices[eud.device_id].links = {};
      devices[eud.device_id].state = deviceInfo[eud.eud_type].defaultState;
      devices[eud.device_id].rank = 1;
      xPos = xPos + 150;
      refreshDevice(eud.device_id);
    })
  }
  if(system.config.devices.pvs){
  system.config.devices.pvs.forEach(function(pv){
    if(!pv.grid_controller_id){
      pv.grid_controller_id = findGridControllerId(pv.device_id);
    }
    if(pv.grid_controller_id){
      createLink(pv.device_id, pv.grid_controller_id);
    }
  })
  }
  if(system.config.devices.utility_meters){
  system.config.devices.utility_meters.forEach(function(utm){
    if(!utm.grid_controller_id){
      utm.grid_controller_id = findGridControllerId(utm.device_id);
    }
    if(utm.grid_controller_id){
      createLink(utm.device_id, utm.grid_controller_id);
    }
  })
  }
  if(system.config.devices.euds){
  system.config.devices.euds.forEach(function(eud){
    if(!eud.grid_controller_id){
      eud.grid_controller_id = findGridControllerId(eud.device_id);
    }
    if(eud.grid_controller_id){
      createLink(eud.grid_controller_id, eud.device_id);
    }
  })
  }
  if(system.config.devices.grid_controllers){
    system.config.devices.grid_controllers.forEach(function(gc){
      /*if(!gc.grid_controller_id){
        gc.grid_controller_id = findGridControllerId(gc.device_id);
      }*/
      gc.connected_devices.forEach(function(deviceName){
        if(deviceName.split("_")[0] == "gc"){
          createLink(gc.device_id, deviceName);
        }
      })  
    })
  }
}