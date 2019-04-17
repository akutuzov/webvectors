/* пересобирает результат так, что каждой частоте соответствует массив результатов
на вход получает объект, содержащий для каждой модели перечень слов с его значением частотности
{модель:{фильтра(частота):{значение:[подходящие слова]}}}
*/
function makeListForEachFrequency(modelWordInfo, listOfFrequencies, models, filter){
    let newResults = {} // TODO не обязтельно frequencies, сделать под все фильтры
  
    $.each(models, function(index, model){
      // создаём заготовку для представления результатов
      newResults[model] ={};
      newResults[model][filter] = {};
      // создаём пустой список для каждой частоты
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
  
  // смотрим на чекбоксы и по ним формируем массив подходящих слов
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
  
  // обращается к списку для каждой модели по id <ol>
  // показывает не более 10 результатов - <li>, если его текст входит в массив
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
  
  // проверяем чекбоксы при запуске страницы и при любом клике
  $(document).ready(function(){
    const RESULTS = JSON.parse($("#result").data("result").replace(/'/g, '"'));
    const FREQUENCIES = ['high', 'mid', 'low'];
    const MODELS = Object.keys(RESULTS);
    const FILTER = 'freq';
    const MAXNUM = ($('title').text() == 'WebVectors: Semantic Calculator' || $('title').text() == 'WebVectors: Семантический калькулятор') ? 5 : 10

    let sortedResults = (makeListForEachFrequency(RESULTS, FREQUENCIES, MODELS, FILTER));
    let output = checkFrequencyMakeOutput(sortedResults, FREQUENCIES, FILTER);
    formResultsUsingFilterList(output, MAXNUM);
    $(".checkbox").change(function(){
      let output = checkFrequencyMakeOutput(sortedResults, FREQUENCIES, FILTER);
      formResultsUsingFilterList(output, MAXNUM);
    });
  });