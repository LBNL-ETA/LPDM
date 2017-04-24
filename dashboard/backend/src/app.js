var express = require('express');
var path = require('path');
var favicon = require('serve-favicon');
var logger = require('morgan');
var cookieParser = require('cookie-parser');
var bodyParser = require('body-parser');
var cmd = require('node-cmd');

var index = require('./routes/index');
var download_tag = require('./routes/download_tag');
//var users = require('./routes/users');
//var simulation = require('./routes/simulation');
//var simulation_data = require('./routes/simulation_data');

var socket_io = require("socket.io")
var app = express();

var io = socket_io();
app.io = io;

// setup the socket handlers
var lpdm_sockets = require('./lpdm_sockets')(io);

// view engine setup
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'jade');

// uncomment after placing your favicon in /public
//app.use(favicon(path.join(__dirname, 'public', 'favicon.ico')));
app.use(logger('dev'));
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: false }));
app.use(cookieParser());
app.use(require('node-sass-middleware')({
    src: '/frontend/src',
    dest: '/frontend/src',
    indentedSyntax: true,
    sourceMap: true
}));
app.use(express.static('/frontend/src'));
app.use('/lib', express.static('/frontend/node_modules'));
app.use('/download_tag', download_tag);

// setup the handlers for the api
//app.use('/', index);
//app.use('/api/simulation', simulation);
//app.use('/api/simulation_data', simulation_data);

// catch 404 and forward to error handler
app.use(function(req, res, next) {
    var err = new Error('Not Found');
    err.status = 404;
    next(err);
});

// error handler
app.use(function(err, req, res, next) {
    // set locals, only providing error in development
    res.locals.message = err.message;
    res.locals.error = req.app.get('env') === 'development' ? err : {};

    // render the error page
    res.status(err.status || 500);
    res.render('error');
});

module.exports = app;
