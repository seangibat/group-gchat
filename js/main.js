toggleSound = function(){
  if (glob.sound == true){
    glob.sound = false;
    $('#soundIcon').removeClass('fa-volume-up');
    $('#soundIcon').addClass('fa-volume-off');
  }
  else{
    glob.sound = true;
    $('#soundIcon').removeClass('fa-volume-off');
    $('#soundIcon').addClass('fa-volume-up');
  }
}

createUID = function(){
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, 
    function(c) {var r = Math.random()*16|0,v=c=='x'?r:r&0x3|0x8;return v.toString(16);});
};

scrollToBottom = function(){
  window.scrollTo(0,document.body.scrollHeight);
};

turnLinksBlue = function(element){
  element.html(Autolinker.link(element.html()));
};

$.fn.turnLinksBlue = function() {
  return this.each(function() {
    $(this).html(Autolinker.link($(this).html()));
  });
};

$.fn.makeChatroomsLinkable = function() {
  var patt = /(^\/|\s\/)\w+/ig;
  return this.each(function() {
    $(this).html($(this).html().replace(patt,function(match){
      return "<a href='" + match + "' target='_blank'>" + match + "</a>";
    }));
  });
};

breakLongWords = function(element){
  var patt = /([^\s<>]{20})(?![^<>]*>)/gi;
  element.html(element.html().replace(patt,function(match){
    console.log(match);
    return match + "&#8203;";
  }));
};

channel = new goog.appengine.Channel(glob.token);
socket = channel.open();

socket.onmessage = function(data){
  obj = JSON.parse(data.data);
  uid = createUID();

  $('#chatsContainer').append("<tr id="+uid+"><td class='author'>" 
    + obj.author + "</td><td class='content'>" + obj.content + "</td></tr>");

  breakLongWords($('#'+uid+' td:nth-child(2)'));
  scrollToBottom();
  turnLinksBlue($('#'+uid+' td:nth-child(2)'));
  $('#'+uid+' td:nth-child(2)').makeChatroomsLinkable();

  $.titleAlert("New Message From " + obj.author, {requireBlur:true, stopOnFocus:true, duration:10000, interval:500});

  if (glob.sound && (glob.userNickname != obj.author)) play_multi_sound('dingSound');
};

$('#chatInput').keydown(function(event){
  var code = event.keyCode || event.which;
  if(code == 13) { // Enter keycode
    event.preventDefault();
    userInput = $('#chatInput').val();
    $('#chatInput').val('');
    $.post("/chatpost", {content: userInput, chatroom: glob.chatroom});
  }
});

$(function() {
  $('#chatInput').focus();
  $(window).focus(function(){$('#chatInput').focus();});
  breakLongWords($('#chatsContainer'));
  scrollToBottom();
  $('.content').turnLinksBlue();
  $('.content').makeChatroomsLinkable();

  $('#connectedUsers').hide();
  $('#connectedUsersLabel').click(function(){
    $('#connectedUsers').slideToggle();
  });
});