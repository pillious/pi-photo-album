/*
Settings Logic
*/
const handleSettingsSubmit = (e) => {
    e.preventDefault();
    showLoadingSpinnerWithCaption('Saving settings...');

    // Confirmation dialog
    if (!confirm('Are you sure?')) {
        return;
    }

    const fields = new FormData(e.target);

    const newState = {
        album: fields.get('album').trim(),
        isEnabled: Math.min(parseInt(fields.get('isEnabled')), 1) === 1,
        blend: clamp(parseInt(fields.get('blend')), 0, 1000),
        speed: clamp(parseInt(fields.get('speed')), 0, 180),
        randomize: fields.get('randomize') === 'on',
    };

    // Save state if changed
    if (
        settingsState.album !== newState.album ||
        settingsState.blend !== newState.blend ||
        settingsState.speed !== newState.speed ||
        settingsState.randomize !== newState.randomize ||
        settingsState.isEnabled !== newState.isEnabled
    ) {
        const saved = saveSettingsState(newState);
        if (saved) {
            updateSettingsUI(newState);
            console.log('Saved: ', newState);
        } else {
            alert('Failed to save settings');
        }
    }
    hideLoadingSpinner();
};

const handleResetToDefault = () => {
    saveSettingsState(DEFAULT_SETTINGS);
    updateSettingsUI(DEFAULT_SETTINGS);
};

const updateSettingsUI = (newState) => {
    settingsState = { ...newState };
    console.log(settingsState)
    const form = document.getElementById('slideshow-settings');
    form.elements.namedItem('isEnabled').value = settingsState.isEnabled ? 1 : 0;
    form.elements.namedItem('blend').value = settingsState.blend;
    form.elements.namedItem('speed').value = settingsState.speed;
    form.elements.namedItem('randomize').checked = settingsState.randomize;

    document.getElementById('blend-current-value').innerHTML = settingsState.blend;
    document.getElementById('speed-current-value').innerHTML = settingsState.speed;

    // Populate the album select dropdown
    const albumSelect = form.elements.namedItem('album');
    albumSelect.innerHTML = albumSelect.firstElementChild.outerHTML;
    
    const albumPaths = removeAlbumsPrefixes(getAlbumPaths(fileSystemSnapshot, true))
    for (const path of albumPaths) {
        const option = document.createElement('option');
        option.value = path;
        option.innerHTML = path;
        albumSelect.appendChild(option);
    }
    // Set the selected album
    albumSelect.value = settingsState.album;
};

const saveSettingsState = async (state) => {
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