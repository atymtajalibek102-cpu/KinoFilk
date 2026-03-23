document.addEventListener('DOMContentLoaded', function () {
    var loginTab     = document.getElementById('loginTab');
    var registerTab  = document.getElementById('registerTab');
    var loginForm    = document.getElementById('loginForm');
    var registerForm = document.getElementById('registerForm');

    loginTab.addEventListener('click', function () {
        loginTab.classList.add('active');
        registerTab.classList.remove('active');
        loginForm.classList.add('active');
        registerForm.classList.remove('active');
    });

    registerTab.addEventListener('click', function () {
        registerTab.classList.add('active');
        loginTab.classList.remove('active');
        registerForm.classList.add('active');
        loginForm.classList.remove('active');
    });
});

function togglePassword(fieldId, toggleElement) {
    const field = document.getElementById(fieldId);
    const icon = toggleElement.querySelector('i');
    if (field.type === 'password') {
        field.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        field.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}