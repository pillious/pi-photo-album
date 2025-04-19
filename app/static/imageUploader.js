/*
Image Upload Logic
*/
const handleFileUploadChange = (e) => {
    const files = e.target.files;
    for (const file of files) {
        let fileName = secureFilename(file.name);
        // Using hash over uuid to prevent duplicate filenames in staging.
        filesInStaging[String(cyrb53(fileName))] = {
            fileContent: file,
            album: '',
            fileName,
        };
    }

    // Clear the invisible file input after getting the files.
    e.target.value = null;

    console.log(files);
    console.log(filesInStaging);
    updateFileStagingUI();
};

const updateFileStagingUI = () => {
    const stagingList = document.getElementById('image-staging-list');
    stagingList.innerHTML = '';

    const albumPaths = getAlbumPaths(fileStructureSnapshot, false).map(
        (path) => path.substring(path.indexOf('/') + 1) // Remove the leading 'albums/'
    );

    console.log(filesInStaging);

    for (const [id, { album, fileName }] of Object.entries(filesInStaging)) {
        const listItem = createStagedFileUI(fileName, album, albumPaths);
        listItem.querySelector('.staging-remove-btn').onclick = () => {
            const isFirstChild = listItem === stagingList.firstElementChild;

            delete filesInStaging[id];
            stagingList.removeChild(listItem);

            updateUploadButtonState();
            if (isFirstChild) createSetAlbumForAllBtn();
        };
        listItem.querySelector('.staging-album-selector').onchange = (e) => {
            filesInStaging[id].album = e.target.value;
        };

        stagingList.appendChild(listItem);
    }

    createSetAlbumForAllBtn();
    updateUploadButtonState();
};

const createStagedFileUI = (fileName, album, albumPaths) => {
    const listItem = document.createElement('li');
    listItem.innerHTML = fileName;

    // Remove file btn
    const removeBtn = document.createElement('button');
    removeBtn.classList.add('staging-remove-btn');
    removeBtn.innerHTML = 'x';
    listItem.prepend(removeBtn);

    // Album selector
    const selectorTitle = "<option value='' disabled>-- Select an Album --</option>";
    const albumInput = document.createElement('select');
    albumInput.classList.add('staging-album-selector');
    albumInput.innerHTML = selectorTitle;
    albumInput.value = album;
    albumPaths.forEach((path) => {
        const option = document.createElement('option');
        option.innerHTML = path;
        option.value = path;
        albumInput.appendChild(option);
    });
    listItem.append(albumInput);

    return listItem;
};

const createSetAlbumForAllBtn = () => {
    const firstListItem = document.getElementById('image-staging-list').firstElementChild;
    if (firstListItem) {
        const setAlbumForAllBtn = document.createElement('button');
        setAlbumForAllBtn.type = 'button';
        setAlbumForAllBtn.id = 'set-album-for-all-btn';
        setAlbumForAllBtn.innerHTML = 'Set Album for All';
        setAlbumForAllBtn.onclick = () => {
            const selectors = document.querySelectorAll('.staging-album-selector');
            const albumPath = selectors[0].value;
            let count = 0;
            for (const id in filesInStaging) {
                filesInStaging[id].album = albumPath;
                selectors[count++].value = albumPath;
            }
        };
        firstListItem.appendChild(setAlbumForAllBtn);
    }
};

const handleImagesUpload = async (e) => {
    e.preventDefault();
    if (Object.keys(filesInStaging).length === 0) return;

    const data = new FormData();
    metadata = { files: {} };
    for (const [id, { fileContent, album, fileName }] of Object.entries(filesInStaging)) {
        // Preliminary validation
        if (!isImageFile(fileName)) {
            alert(
                'Files must be one of the following types: ' + ALLOWED_FILE_EXTENSIONS.join(', ')
            );
            return;
        }
        if (album.trim() === '') {
            alert('Please assign an album to all images.');
            return;
        }
        metadata.files[fileName] = id;
        data.append(album, fileContent);
    }
    data.append('metadata', JSON.stringify(metadata));

    try {
        const resp = await fetch('/upload-images', {
            method: 'POST',
            body: data,
        });
        if (!resp.ok) throw new Error('Failed to upload images');
        const respData = await resp.json();
        console.log(respData);
        if (respData.status !== 'ok') throw new Error('Failed to upload images');
        const newFilesInStaging = {};
        for (const failed of respData.failed ?? []) {
            if (failed in filesInStaging) {
                newFilesInStaging[failed] = filesInStaging[failed];
            }
        }
        alert(
            `Successfully uploaded ${Object.keys(filesInStaging).length - Object.keys(newFilesInStaging).length} image(s).\n\n${'failed' in respData && respData.failed.length > 0 ? 'Failed to upload:' : ''}\n${Object.keys(
                newFilesInStaging
            )
                .map((id) => filesInStaging[id].fileName)
                .join('\n')}`
        );

        // All successfully uploaded files removed from staging & added to file system.
        for (const id in filesInStaging) {
            if (!(id in newFilesInStaging)) {
                const { album, fileName } = filesInStaging[id];
                updateFileSystem('', album + '/' + fileName);
            }
        }
        filesInStaging = newFilesInStaging;
        updateFileSystemUI();
        updateFileStagingUI();
    } catch (e) {
        console.error(e);
        alert('Failed to upload images.');
    }
};

const updateUploadButtonState = () => {
    const uploadBtn = document.getElementById('upload-submit-btn');
    uploadBtn.disabled = Object.keys(filesInStaging).length === 0;
};
