// reassembles the result, input: {model:{word:[number, value]}}, output: {model:{filter:{value:[matching words]}}}
function makeListForEachFrequency(modelWordInfo, listOfFrequencies, models, filter){
  let newResults = {};

  $.each(models, function(index, model){
    // create a template for the results
    newResults[model] ={};
    newResults[model][filter] = {};
    $.each(listOfFrequencies, function(index, frequency){
      newResults[model][filter][frequency]=[];

      $.each(modelWordInfo[model], function(word, values){
        if (values[1] == frequency){
          newResults[model][filter][frequency].push(word);
        };
      });
    });
  });
  return newResults;
};

// form an array of appropriate words according to the checkbox
function checkFrequencyMakeOutput(allFilters, frequenciesList, filter){
  let resultChecked = {};
  $.each(allFilters, function(model,data){
    resultChecked[model]=[];
  });
  $.each(frequenciesList, function(index,value){
    if ($("#"+value).is(':checked')){
      $.each(allFilters, function(model,data){
        resultChecked[model] = resultChecked[model].concat(allFilters[model][filter][value]);
      });
    };
  });
  return resultChecked;
};

// show no more than 10 words matching with the resulting array
function formResultsUsingFilterList(resultArray, maxNumber){ 
  $("ol").each(function(){ 
    let currentModel=$(this).attr("id");
    let counter = 0;
    $("#"+currentModel).children("li").each(function(){
      if ($.inArray($(this).data("word"), resultArray[currentModel]) > -1 && counter < maxNumber){
        $(this).fadeIn('slow');
        counter ++;
      } else {
        $(this).fadeOut('slow');
      };
    });
  });
};

$(document).ready(function(){
  const MAXNUM = $("#result").data("visible");
  const RESULTS = $("#result").data("result");
  const MODELS = Object.keys(RESULTS);
  const FREQUENCIES = ['high', 'mid', 'low'];
  const FILTER = 'freq';
  
  let sortedResults = (makeListForEachFrequency(RESULTS, FREQUENCIES, MODELS, FILTER));
  let output = checkFrequencyMakeOutput(sortedResults, FREQUENCIES, FILTER);
  formResultsUsingFilterList(output, MAXNUM);
  $(".checkbox").change(function(){
    let output = checkFrequencyMakeOutput(sortedResults, FREQUENCIES, FILTER);
    formResultsUsingFilterList(output, MAXNUM);
  });
})
