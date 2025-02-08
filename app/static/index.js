const defaultState = {
    isEnabled: true,
    blend: 250,
    speed: 30,
    randomize: false,
};
const formId = 'slideshow';

let state = { ...defaultState };

const handleSettingsSubmit = (e) => {
    e.preventDefault();

    // Confirmation dialog
    if (!confirm('Are you sure?')) {
        return;
    }

    const fields = new FormData(e.target);

    const newState = {
        isEnabled: Math.min(parseInt(fields.get('isEnabled')), 1) === 1,
        blend: clamp(parseInt(fields.get('blend')), 0, 1000),
        speed: clamp(parseInt(fields.get('speed')), 0, 180),
        randomize: fields.get('randomize') === 'on',
    };

    // Save state if changed
    if (
        state.blend !== newState.blend ||
        state.speed !== newState.speed ||
        state.randomize !== newState.randomize ||
        state.isEnabled !== newState.isEnabled
    ) {
        const saved = saveState(newState);
        if (saved) {
            updateStateUI(newState);
            console.log('Saved: ', newState);
        } else {
            alert('Failed to save settings');
        }
    }
};

const handleResetToDefault = () => {
    saveState(defaultState);
    updateStateUI(defaultState);
};

const updateStateUI = (newState) => {
    state = { ...newState};
    const form = document.getElementById(formId);
    form.elements.namedItem('isEnabled').value = state.isEnabled ? 1 : 0;
    form.elements.namedItem('blend').value = state.blend;
    form.elements.namedItem('speed').value = state.speed;
    form.elements.namedItem('randomize').checked = state.randomize;

    document.getElementById('blend-current-value').innerHTML = state.blend;
    document.getElementById('speed-current-value').innerHTML = state.speed;
};

// [POST] /save-settings
const saveState = async (state) => {
    const resp = await fetch('/save-settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(state),
    });
    const respObj = await resp.json();
    if (respObj.status !== 'ok') {
        console.error('Failed to save settings', respObj);
    }
    return respObj.status === 'ok';
};

/// Image Upload Logic
let filesInStaging = {};

const handleFileUploadChange = (e) => {
    const files = e.target.files;
    console.log(files)

    for (const file of files) {
        filesInStaging[file.name] = file;
    }

    // Clear input
    e.target.value = null;

    console.log(filesInStaging);
    updateFileStagingUI();
}

const updateFileStagingUI = () => {
    const stagingList = document.getElementById('image-staging-list');
    stagingList.innerHTML = '';

    for (const fileName in filesInStaging) {
        const li = document.createElement('li');
        li.innerHTML = fileName;

        const removeBtn = document.createElement('button');
        removeBtn.classList.add('staging-remove-btn')
        removeBtn.innerHTML = 'x';
        removeBtn.onclick = () => {
            delete filesInStaging[fileName];
            stagingList.removeChild(li)
        };

        li.prepend(removeBtn);

        stagingList.appendChild(li);
    }
}

const handleImagesUpload = async (e) => {
    e.preventDefault();

    const data = new FormData();

    for (const file of Object.values(filesInStaging)) {
        console.log(file);
        data.append('file', file)
    }

    const resp = await fetch('/upload-images', {
        method: 'POST',
        body: data,
    });
    const r = await resp.text();
    console.log(r);
    console.log(resp.ok)

    if (resp.ok) {
        // Clear staging
        filesInStaging = {};
        updateFileStagingUI();
    }
}

// On page load
document.addEventListener('DOMContentLoaded', () => {
    console.log(savedSettings);
    updateStateUI(savedSettings);

    document.getElementById('blend').addEventListener('input', (e) => {
        document.getElementById('blend-current-value').innerHTML = e.target.value;
    });

    document.getElementById('speed').addEventListener('input', (e) => {
        document.getElementById('speed-current-value').innerHTML = e.target.value;
    });

    document.getElementById('image-upload-btn').addEventListener('click', 
        () => document.getElementById('image-upload-input-hidden').click()
    );
});

// Utils
const clamp = (val, min, max) => {
    return Math.min(Math.max(val, min), max);
};

