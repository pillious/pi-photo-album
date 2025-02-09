const defaultState = {
    album: 'alee1246/nature ',
    isEnabled: true,
    blend: 250,
    speed: 30,
    randomize: false,
};
let state = { ...defaultState };

const handleSettingsSubmit = (e) => {
    e.preventDefault();

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
        state.album !== newState.album ||
        state.blend !== newState.blend ||
        state.speed !== newState.speed ||
        state.randomize !== newState.randomize ||
        state.isEnabled !== newState.isEnabled
    ) {
        const saved = saveState(newState);
        if (saved) {
            updateSettingsUI(newState);
            console.log('Saved: ', newState);
        } else {
            alert('Failed to save settings');
        }
    }
};

const handleResetToDefault = () => {
    saveState(defaultState);
    updateSettingsUI(defaultState);
};

const updateSettingsUI = (newState) => {
    state = { ...newState };
    const form = document.getElementById('slideshow');
    form.elements.namedItem('album').value = state.album;
    form.elements.namedItem('isEnabled').value = state.isEnabled ? 1 : 0;
    form.elements.namedItem('blend').value = state.blend;
    form.elements.namedItem('speed').value = state.speed;
    form.elements.namedItem('randomize').checked = state.randomize;

    document.getElementById('blend-current-value').innerHTML = state.blend;
    document.getElementById('speed-current-value').innerHTML = state.speed;
};

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

/*
Image Upload Logic
*/
let filesInStaging = {};

const handleFileUploadChange = (e) => {
    const files = e.target.files;
    console.log(files);

    for (const file of files) {
        filesInStaging[file.name] = file;
    }

    // Clear input
    e.target.value = null;

    console.log(filesInStaging);
    updateFileStagingUI();
};

const updateFileStagingUI = () => {
    const stagingList = document.getElementById('image-staging-list');
    stagingList.innerHTML = '';

    for (const fileName in filesInStaging) {
        const li = document.createElement('li');
        li.innerHTML = fileName;

        const removeBtn = document.createElement('button');
        removeBtn.classList.add('staging-remove-btn');
        removeBtn.innerHTML = 'x';
        removeBtn.onclick = () => {
            delete filesInStaging[fileName];
            stagingList.removeChild(li);
        };

        li.prepend(removeBtn);

        stagingList.appendChild(li);
    }
};

const handleImagesUpload = async (e) => {
    e.preventDefault();

    const TEMP_DIR = 'alee1246/nature';

    const data = new FormData();
    for (const file of Object.values(filesInStaging)) {
        console.log(file);
        data.append(TEMP_DIR, file);
    }
    try {
        const resp = await fetch('/upload-images', {
            method: 'POST',
            body: data,
        });
        if (!resp.ok)
            throw new Error('Failed to upload images');
        const respData = await resp.json();
        console.log(respData);
        if (respData.status !== 'ok') 
            throw new Error('Failed to upload images'); 
        const newFilesInStaging = {};
        for (const failed of respData.failed) {
            if (failed in filesInStaging) {
                newFilesInStaging[failed] = filesInStaging[failed];
            }
        }
        alert(
            `Successfully uploaded ${Object.keys(filesInStaging).length - Object.keys(newFilesInStaging).length} image(s).
            
            ${respData.failed.length > 0 ? "Failed to upload:" : ""}
            ${Object.keys(newFilesInStaging).join("\n")}`
        );
        filesInStaging = newFilesInStaging;
        updateFileStagingUI();
    } catch (e) {
        console.error(e);
        alert('Failed to upload images.');
    }
};

/*
File System Logic
*/
const updateFileSystemUI = (fileStructure) => {
    const fileSystemTreeRoot = document.getElementById('file-system-tree');
    fileSystemTreeRoot.innerHTML = '';

    const stack = [];
    stack.push([fileStructure.albums, 'file-system-tree'])
    
    while (stack.length > 0) {
        const [fsObj, elemId] = stack.pop();
        const parent = document.getElementById(elemId)
        const parentPath = parent.getAttribute('data-album-path') || '';
        for (const [key, val] of Object.entries(fsObj)) {
            if (typeof val === "object") {
                // Folder Name List Item
                const folderLi = document.createElement('li');
                folderLi.classList.add('album-name');
                folderLi.innerHTML = key;
                folderLi.setAttribute('data-album-path', parentPath + '/' + key);
                parent.appendChild(folderLi);

                // Folder Sublist
                const folderUl = document.createElement('ul');
                folderUl.id = key;
                folderUl.setAttribute('data-album-path', parentPath + '/' + key);
                folderUl.style.display = 'none'; // Defaults to hiding files
                parent.appendChild(folderUl);
            
                // Button to hide files in folder
                const hideBtn = document.createElement('button');
                hideBtn.innerHTML = 'Hide';
                hideBtn.classList.add('hide-album-btn');
                hideBtn.onclick = () => {
                    folderUl.style.display = folderUl.style.display === 'none' ? 'block' : 'none';
                    hideBtn.innerHTML = folderUl.style.display === 'none' ? 'Show' : 'Hide';
                };

                // Button to create a subfolder
                const createAlbumBtn = document.createElement('button');
                createAlbumBtn.innerHTML = 'Create Album';
                createAlbumBtn.classList.add('create-album-btn');
                createAlbumBtn.onclick = () => {
                    const albumName = prompt('Enter album name');
                    // TODO: fix the file structure path
                    if (albumName !== null && albumName.trim() !== '' && !(albumName in val)) {
                        val[albumName] = {};
                        updateFileSystemUI(fileStructure);
                    }
                };
                
                folderLi.appendChild(hideBtn);
                folderLi.appendChild(createAlbumBtn);

                stack.push([val, key]);
            } else {
                const fileLi = document.createElement('li');
                fileLi.innerHTML = key;
                fileLi.setAttribute('data-album-path', parentPath + '/' + key);
                parent.appendChild(fileLi);
            }
        }
    }
}

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

// Utils
const clamp = (val, min, max) => {
    return Math.min(Math.max(val, min), max);
};
