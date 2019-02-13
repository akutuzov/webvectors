$(document).ready(function(){
    $("#high").click(function(){
      if ($(this).is(':checked')){
        $("li.high").fadeIn('slow');
      } else {$("li.high").fadeOut('slow');}
    });
    $("#mid").click(function(){
      if ($(this).is(':checked')){
        $("li.mid").fadeIn('slow');
      } else {$("li.mid").fadeOut('slow');}
    });
    $("#low").click(function(){
      if ($(this).is(':checked')){
        $("li.low").fadeIn('slow');
      } else {$("li.low").fadeOut('slow');}
    });
  });