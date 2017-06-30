var template = '<div class="input-group"><input type="text" class="form-control" name="list_query" maxlength=200 /></div>',
    minusButton = '<span class="btn input-group-addon delete-field">(–)</span>';

$('.add-field').click(function() {
    var temp = $(template).insertBefore('.help-block');
    temp.append(minusButton);
});

$('.fields').on('click', '.delete-field', function(){
    $(this).parent().remove();
});
