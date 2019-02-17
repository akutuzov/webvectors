$(document).ready(function(){
  var freq = ['high', 'mid', 'low']
    $.each(freq, function(index,value){
      $("#"+value).click(function(){
        if ($(this).is(':checked')){
          $("li."+value).fadeIn('slow');
        } else {$("li."+value).fadeOut('slow');}
      });
    });
  });
  