
function AJAX(container, url, data = {}, propertyNames = [], callback = null) {

	// console.log('AJAX(' + [container, url, data, propertyNames, callback] + ')');
	// startAnimation();

	if (container == '#action') {
		data["inline"] = "true";
	}

	for (var i in propertyNames) {

		// Process values
		key = propertyNames[i];
		if (typeof (key) != 'function') {

			if ($('#' + key).is('input:checkbox')) {
				if ($('#' + key + ':checked').val()) {
					value = 'on';
				}
				else {
					value = '';
				}
			}
			else if ($("input:radio[name='" + key + "']").is('input:radio')) {
				value = $("input:radio[name='" + key + "']:checked").val();
			}
			else if ($('#' + key).is('input:file')) {
				value = document.getElementById(key).files[0];
			}
			else {
				value = $('#' + key).val();
			}

			if (value == undefined) {
				value = '__undefined__';
			}

			data[key] = value;

			// console.log(data);

		}
	}


	$.post(url, data)
		.done(function (response, statusText, xhr) {

			// console.log(response);

			if (xhr.status == 204) {
				hideDialog();
			}
			else if (xhr.status == 200) {
				if (container) {
					$(container).html(response);


				}
				else if (callback) {
					callback(response);
				}
			}

			enableButtons();
			// stopAnimation();
			documentReady();

		})
		.fail(function (xhr, textStatus, errorThrown) {

			console.log(xhr.status, xhr.responseText);

			if (xhr.status == 500) {
				warning(xhr.responseText);
			}

			else if (xhr.status == 900) {
				$('#action').html(xhr.responseText);
			}

			enableButtons();
			stopAnimation();
			documentReady();

		})

}

function handleChoiceValue(actualItem, choiceItem, choiceValue) {
	val = choiceItem.val();
	values = actualItem.val().split(',');
	if (val) {
		if (!values.includes(choiceValue)) {
			values.push(choiceValue);
		}
	}
	else {
		if (values.includes(choiceValue)) {
			var index = values.indexOf(choiceValue);
			if (index !== -1) {
				values.splice(index, 1);
			}
		}
	}
	actualItem.val(values.join(","));
}

function dialogConfirm(message, container, URL) {
	if (confirm(message)) {
		AJAX($(container), URL);
		enableButtons();
		return true;
	}
	else {
		enableButtons();
		return false;
	}
}


function warning(text) {
	enableButtons();
	window.alert(text);
	enableButtons();
}

function info(text) {
	enableButtons();
	window.alert(text);
	enableButtons();
}

function stopAnimation() {

}

function startAnimation() {

}

function showLogin() {
	$('#login').removeClass('login');
	$('#login').removeClass('createAccount');
	$('#login').addClass('login');

	$("#login").ready(function () {
		$('#login').css('height', 'auto');
		$('#login').css('height', ($('#login .dialogInnerInnerInnerWrapper').outerHeight()) + 190) + 'px';
	});

	$('#login').fadeIn();
}

function showCreateUserAccount() {
	$('#login').removeClass('login');
	$('#login').removeClass('createAccount');
	$('#login').addClass('createAccount');

	$("#login").ready(function () {
		$('#login').css('height', 'auto');
		$('#login').css('height', ($('#login .dialogInnerInnerInnerWrapper').outerHeight()) + 190) + 'px';
	});

	$('#login').fadeIn();
}

function hideLogin() {
	$('#login').fadeOut(300, function () {
		$('#login').removeClass('login');
		$('#login').removeClass('createAccount');

		$('#name').val('');
		$('#username').val('');
		$('#password').val('');
		$('#password2').val('');

		enableButtons();
	});

	enableButtons();
}

scrollTop = 0;

function dialog(url) {
	AJAX('#dialog .dialogContent', url);

	// $('body').css('position', 'fixed');
	$('body').css('overflow', 'hidden');
}

function hideDialog() {
	$('#dialog').fadeOut(function () { enableButtons(); $('body').css('overflow', 'auto'); });

	// $('body').css('position', 'static');

}

function login(username, password) {
	AJAX('#action', '/login', { 'username': username, 'password': password, 'inline': 'true' });
}

function logout() {
	AJAX('#action', '/logout');
}

function enableButtons() {
	$('.disabled').removeClass('disabled');
	$('.button,button').click(function () {
		$(this).addClass('disabled');
	});
}

function deRequiredMissing(element) {
	$(element).removeClass('requiredmissing');
}

function createUserAccount(name, email, password1, password2) {

	if (!name || !email || !password1 || !password2) {
		enableButtons();
		warning('At least one required fields is empty.');
		enableButtons();
	}

	else if (password1 != password2) {
		enableButtons();
		warning('Passwords don’t match.');
		enableButtons();
	}

	else {
		AJAX(null, '/v1/createUserAccount', { 'name': name, 'email': email, 'password': password1, 'inline': 'true' }, null, processCreateUserAccount);
	}

}

function processCreateUserAccount(data) {

	if (data.response == 'userExists') {
		enableButtons();
		warning('User already exists');
	}
	else if (data.response == 'emailInvalid') {
		enableButtons();
		warning('Email address is invalid');
	}
	else if (data.response == 'success') {
		enableButtons();
		login($('#username').val(), $('#password').val());
	}
}

function dataContainerJavaScriptIdentifier(element) {
	if (element.closest('.dataContainer' && element.closest('.dataContainer').attr('class'))) {
		if (element.closest('.dataContainer').attr('class')) {
			return element.closest('.dataContainer').attr('class').split(' ')[1];
		}
		else {
			return '';
		}
	}
	else {
		return '';
	}
}

function reload(element, parameters) {
	url = '/reloadContainer?inline=true&dataContainer=' + dataContainerJavaScriptIdentifier(element);
	if (parameters != undefined) {
		url += "&parameters=" + JSON.stringify(parameters)
	}
	AJAX('.' + dataContainerJavaScriptIdentifier(element), url);
}

$(document).ready(function () {
	$('.button,button').click(function () {
		if (!$(this).attr("href")) {
			$(this).addClass('disabled');
		}
	});
	documentReady();
});

function documentReady() {
	makeTOC();
	resize();

	$("#autotoc a").click(function () {
		if ($(".autotoc.category[title='" + $(this).attr('title') + "']").length) {
			el = $(".autotoc.category[title='" + $(this).attr('title') + "']");
		}
		else if ($(".autotoc.subcategory[title='" + $(this).attr('title') + "']").length) {
			el = $(".autotoc.subcategory[title='" + $(this).attr('title') + "']");
		}

		if (el) {
			$("html, body").animate({ scrollTop: el.offset().top - 20 }, 500);
		}

	});
}

function makeTOC() {
	html = '';

	if ($("#autotoc").length) {
		previous = null;
		$(".autotoc.category, .autotoc.subcategory").each(function (index) {

			html += '<ul>';
			if ($(this).hasClass("category")) {

				if (previous) {
					html += '</ul>';
					html += '<li>';
				}

				html += '<li>';
				html += '<a title="' + $(this).attr("title") + '">';
				html += $(this).attr("title");
				html += '</a>';

				if ($(this).find(".autotoc.subcategory")) {
					html += '<ul>';
				}

				previous = $(this);
			}
			if ($(this).hasClass("subcategory")) {
				html += '<li>';
				html += '<a title="' + $(this).attr("title") + '">';
				html += $(this).attr("title");
				html += '</a>';
				html += '</li>';
			}
			html += '</ul>';






		});

		$("#autotoc").html(html);
	}
}

// function pushState(title, url) {

// 	console.log(url);
// 	History.pushState(null, title, url);

// }

// $(document).ready(function(event) {

//     // Prepare
//     var History = window.History; // Note: We are using a capital H instead of a lower h
//     if ( !History.enabled ) {
//          // History.js is disabled for this browser.
//          // This is because we can optionally choose to support HTML4 browsers or not.
//         return false;
//     }

//     // Bind to StateChange Event
//     History.Adapter.bind(window,'statechange',function() { // Note: We are using statechange instead of popstate
//         var State = History.getState();

// 		if (! State.url.indexOf("locale") > -1) {

// 			_currentURL = window.location.protocol + '//' + window.location.host + currentURL
// //			_currentURL = currentURL

// //			Debug('History Adapter:\nCurrent URL' + _currentURL + '\nState.url: ' + State.url);

// 			if (_currentURL != State.url) {
// //				Debug('Reload triggered by History Adapter. currentURL: ' + _currentURL + ', State.url: ' + State.url);
// //				Debug('loadPage(' + State.url.URLfolder() + ')');
// 				loadPage(State.url.URLfolder(), true);

// 			}

// 			else {
// //				Debug('History Adapter is not reloading.');
// 			}

// //		loadPage(State.url.URLfolder(), true);



// 		}
// 	});

// 	documentReady();

// });


$.fn.isInViewport = function () {
	var elementTop = $(this).offset().top;
	var elementBottom = elementTop + $(this).outerHeight();

	var viewportTop = $(window).scrollTop();
	var viewportBottom = viewportTop + $(window).height();

	return elementBottom > viewportTop && elementTop < viewportBottom;
};

$.fn.viewportPart = function () {
	var elementTop = $(this).offset().top;
	var elementBottom = elementTop + $(this).outerHeight();

	var viewportTop = $(window).scrollTop();
	var viewportBottom = viewportTop + $(window).height();

	if (elementBottom > viewportTop && elementTop < viewportBottom) {
		return $(this).outerHeight();
	}
	else if (elementBottom > viewportBottom && elementTop < viewportTop) {
		return $(this).outerHeight();
	}
	else if (elementBottom > viewportTop) {
		return elementBottom - viewportTop;
	}
	else if (elementTop < viewportBottom) {
		return elementTop - viewportBottom;
	}
};

$.fn.portionInViewport = function () {
	var elementTop = $(this).offset().top;
	var elementBottom = elementTop + $(this).outerHeight();

	var viewportTop = $(window).scrollTop();
	var viewportBottom = viewportTop + $(window).height();

	// element is not visible
	if (elementTop > viewportBottom || elementBottom < viewportTop) {
		return 0;
	}

	// element is partially visible, cut off at the top
	else if (elementTop < viewportTop && elementBottom < viewportBottom) {
		return elementBottom - viewportTop;
	}

	// element is partially visible, cut off at the bottom
	else if (elementTop < viewportBottom && elementBottom > viewportBottom) {
		return viewportBottom - elementTop;
	}

	// element is fully visible
	else if (elementBottom > viewportTop && elementTop < viewportBottom) {
		return $(this).outerHeight();
	}

};

$.fn.mostVisible = function () {
	mostVisible = null;
	mostVisiblePortion = 0;
	$(this).each(function (index) {
		if ($(this).portionInViewport() > $(window).height() / 2.0 && $(this).portionInViewport() > mostVisiblePortion) {
			mostVisiblePortion = $(this).portionInViewport();
			mostVisible = $(this);
		}
	});
	return mostVisible;
};


function resize() {

	headerTotal = $("#header").outerHeight();
	if ($("#tabs").length) {
		headerTotal += $("#tabs").outerHeight();
	}
	var top = Math.max(0, headerTotal - $(window).scrollTop()) + 5;
	var height = $(window).height() - top;

	$('.stickToTheTop').css('top', top + 'px');
	$('.stickToTheTop').css('height', height + 'px');
}

$(window).scroll(function () {
	resize();
	trackTOC();
});

$(window).on('resize', function () {
	resize();
	trackTOC();
});

function copyGoogleTranslation() {
	val = $('#google_translation').val();
	val = val.replace(/<br \/> /g, '\n');
	$('#dialogform_translation').val(val);
}

function trackTOC() {
	mostVisible = $(".autotoc").mostVisible();
	if (mostVisible) {
		$("#autotoc a").removeClass("selected");
		el = $("#autotoc a[title='" + mostVisible.attr("title") + "']");
		el.addClass("selected");
	}
	// else {
	//     $("tr.visibilityChange").removeClass("selected");
	// }
}


function authorizeOAuthToken(client_id, response_type, redirect_uri, scope, state) {
	AJAX('#action', '/auth/authorize', { 'client_id': client_id, 'response_type': response_type, 'redirect_uri': redirect_uri, 'scope': scope, 'state': state });
}
