// Global Variables
const DEFAULT_SETTINGS = {
    album: 'alee1246/nature',
    isEnabled: true,
    blend: 250,
    speed: 30,
    randomize: false,
};
const ALLOWED_FILE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'heif', 'heic'];

let settingsState = { ...DEFAULT_SETTINGS };

// List[{id: {fileContent: File, album: str, fileName: str}]
let filesInStaging = {};

// On page load
document.addEventListener('DOMContentLoaded', () => {
    console.log(savedSettings);
    console.log(fileStructureSnapshot);
    updateSettingsUI(savedSettings);
    updateFileSystemUI();
    updateFileStagingUI();

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

    document.getElementById('create-folder-dialog').addEventListener('close', () => {
        // To handle case of `close` triggered by clicking out or pressing ESC
        document.querySelector('.overlay').style.display = 'none';
    });
});
