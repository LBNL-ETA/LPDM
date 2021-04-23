$(function() {
  $.get("/api/systemList")
    .done(function(systemList) {
      console.log(systemList);
      systemList.forEach(function(item) {
        $("#systemList").append('<li id="listItem' + item.id +'" class="systemListItem"><a href="/system?id=' + item.id + '"><span class="tab">' + 
        item.name + '</span></a> <a id="delete' + item.id + '" href="#" class="deleteLink"><i class="fas fa-trash-alt"></i></a></li>');
        $("#delete" + item.id).click(function() {
          $.ajax({ 
            url: '/api/system?id=' + item.id, 
            type: 'DELETE',
            contentType: 'application/json', 
            success: function() {
              console.log("deleted system");
              $("#listItem" + item.id).remove();
            }
          })
        })
      })
    })
});