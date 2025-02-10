// On page load
document.addEventListener('DOMContentLoaded', () => {
    console.log(savedSettings);
    updateSettingsUI(savedSettings);

    console.log(fileStructureSnapshot);
    updateFileSystemUI(fileStructureSnapshot);

    document.getElementById('blend').addEventListener('input', (e) => {
        document.getElementById('blend-current-value').innerHTML = e.target.value;
    });

    document.getElementById('speed').addEventListener('input', (e) => {
        document.getElementById('speed-current-value').innerHTML = e.target.value;
    });

    document
        .getElementById('image-upload-btn')
        .addEventListener('click', () =>
            document.getElementById('image-upload-input-hidden').click()
        );
});
