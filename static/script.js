document.addEventListener('DOMContentLoaded', function ()
{
    const input = document.getElementById('image-input');
    const fileNameSpan = document.getElementById('file-name');

    input.addEventListener('change', function () {
        if (this.files && this.files.length > 0) {
            fileNameSpan.textContent = this.files[0].name;
        } else {
            fileNameSpan.textContent = '';
        }
    });
});