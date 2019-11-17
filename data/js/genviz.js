(function(){
'use strict';

document.addEventListener("DOMContentLoaded", function() {

  // parameters of graph
  var maincolor = "#F4B400";
  var force = d3.layout.force().gravity(.05).distance(100).charge(-100);
  var delta = 0;
  var radius = 10;

  // create data to show: only words in list created by filter.js
  function formData(allData, chosenWords){
    var dataToDraw = [];
    $.each(allData, function(index, pair){
      if (chosenWords.includes(pair["source"])){
        if (chosenWords.includes(pair["target"])){
          dataToDraw.push(pair)
        }
        else {return;}
      }
      else {return;}
    });
    return dataToDraw;
  }

  // fill links and nodes by using data
  function formNodesLinks(data, topn, threshold){
    var nodes = [], links = [];
    var order = {};
    order[query] = 0;
    nodes.push({"name":query, color:maincolor});
    for (var k, k = 1; k < data.length; k++) {
      var dif = 1 - data[k]["value"];
      if (delta && delta > dif || !delta) {
        delta = dif;
      }
      var key = data[k]["target"];
      var src = 0;
      var tg = k;
      if (k > topn) {
        src = order[data[k]["source"]];
        tg = order[data[k]["target"]];
      } else {
        nodes.push({"name":data[k]["target"], color:"#DB4437"});
        order[key] = k;
      }
      if (data[k]["value"] > threshold) {
        links.push({"source":src, "target":tg, "value":dif, "key":key});
      }
    }
    return [nodes, links];
  }

  // create and show graph
  function buildGraph(innodes, inlinks, linkstrokewidth, showPOS, svg) {
    d3.selectAll(".link").remove();
    d3.selectAll(".node").remove();
    d3.selectAll("circle").remove();
    force.nodes(innodes).links(inlinks).linkDistance(function(d) {
      var dv = d.value * 100;
      var df = Math.log(dv);
      var koef = isFinite(df) ? df : 1;
      return dv * koef + radius;
    }).start();
    var linksel = svg.selectAll(".link").data(inlinks);
    var link = linksel.enter().append("line").attr("stroke", "#aaa").style("stroke-width", linkstrokewidth || 1);
    var nodesel = svg.selectAll(".node").data(innodes);
    var node = nodesel.enter().append("g").call(force.drag);
    node.append("circle").attr("fill", function(d) {
      return d.color;
    }).style("stroke", "black").style("stroke-width", function(d) {
      return d.page ? 3 : 0;
    }).attr("r", function(d) {
      return d.color == maincolor ? radius * 1.5 : radius;
    });
    node.append("text").text(function(d) {
      return showPOS === true ? d.name : d.name.split("_")[0];
    }).attr("stroke", "#333").attr("dx", 12).attr("dy", ".35em").style("cursor", "default");
    nodesel.exit().remove();
    force.on("tick", function() {
      link.attr("x1", function(d) {
        return d.source.x;
      }).attr("y1", function(d) {
        return d.source.y;
      }).attr("x2", function(d) {
        return d.target.x;
      }).attr("y2", function(d) {
        return d.target.y;
      });
      node.attr("transform", function(d) {
        return "translate(" + d.x + "," + d.y + ")";
      });
    });
  }

  // if page has place to show graph - do it
  if ($("div").is("#graph")){

    // set svg parameters
    var svg = d3.select("svg");
    var width = $("svg").parent().width();
    var height = Math.min(width, 400);
    svg.attr("width", width).attr("height", height);
    force.size([width, height]);

    // model responce data
    var resultsFull = $("#result").data("graph");
    var currentModel=Object.keys(resultsFull);
    var resOfModel = resultsFull[currentModel];
    var query = $("#result").data("query");

    // default user parameters and data
    var linkstrokewidth = 1;
    var topn = 10;
    var threshold = 0.6;
    var showPOS = "false";

    function getParameters(){
      /* don't change number of neighbours by user input
      topn = $("input[type=number][id=topn]").val();
      if (topn > 10){
        topn = 10;
      }
      */
      topn = 10; // remove in case of user input
      threshold = $("input[type=number][id=threshold]").val();
      showPOS = $("input[type=checkbox][id=separator]").is(":checked");
    }

    function drawFiltered(){
      svg.selectAll("*").remove();
      // check all parameters before every drawing
      getParameters();
      // result of frequency selection
      var resFiltered = JSON.parse(sessionStorage.getItem("shownWords"))[currentModel];
      // in case of number of elements of selected frequency less than topn
      topn = Math.min(topn, resFiltered.length);
      var dataToDraw = formData(resOfModel, [query].concat(resFiltered.slice(0,topn)));
      var nodesLinks = formNodesLinks(dataToDraw, topn, threshold);
      buildGraph(nodesLinks[0], nodesLinks[1], linkstrokewidth, showPOS, svg);
    }

    // draw graph first time
    drawFiltered();

    // immediately redraw after frequency change
    $("#frequencyCheck").change(function(){
      drawFiltered();
    });

    // immediately redraw after pos-tag show/hide change
    $("#separator").change(function(){
      drawFiltered();
    });

    // immediately redraw after threshold change
    $("#threshold").change(function(){
      drawFiltered();
    });

    /*
    // use button "refresh" to redraw graph
    $('#redraw').on("click",function() {
      drawFiltered();
    });
    */

    /*
    // use button with id="switch" to change list and graph
    $('#switch').on("click",function() {
      $("#result").find("ol").toggle();
      $("#graph").toggle();
      drawFiltered();
    });
    */
  }
});
}).call(this)