const toasts = Array.from(document.getElementsByClassName('toast'));

toasts.forEach(element => {
	bootstrap.Toast.getOrCreateInstance(element).show();
});