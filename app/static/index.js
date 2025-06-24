// Global Variables
const DEFAULT_SETTINGS = {
    album: 'Shared',
    isEnabled: false,
    blend: 250,
    speed: 30,
    randomize: false,
};
const ALLOWED_FILE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'heif', 'heic'];

let settingsState = { ...DEFAULT_SETTINGS };

// List[{id: {fileContent: File, album: str, fileName: str}]
let filesInStaging = {};

const refreshUI = () => {
    updateSettingsUI(settingsState);
    updateFileSystemUI();
    updateFileStagingUI();
}

// On page load
document.addEventListener('DOMContentLoaded', () => {
    settingsState = savedSettings || { ...DEFAULT_SETTINGS };

    console.log(savedSettings);
    console.log(fileSystemSnapshot);
    refreshUI();

    // Settings section event listeners
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

    // To handle cases of dialog `cancel` triggered by pressing ESC
    document.querySelectorAll('dialog').forEach((dialog) =>
        dialog.addEventListener('cancel', hideOverlay)
    );

    // Sets up listener for Server-Sent Events
    const eventStream = new EventSource('/stream-events');
    eventStream.onmessage = (e) => {
        if (e.data === 'connected') {
            console.log('Connection established to the event stream');
            return;
        }
        // We don't want to process the connection confirmation message.
        handleEvent(e.data);
    };
    // eventStream.onerror = (e) => {
    //     console.error("ERROR: Event stream error", e);
    //     eventStream.close();
    // };
});
