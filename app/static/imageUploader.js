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

    // TODO: Allow images to be uploaded to any existing album.
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
        if (!resp.ok) throw new Error('Failed to upload images');
        const respData = await resp.json();
        console.log(respData);
        if (respData.status !== 'ok') throw new Error('Failed to upload images');
        const newFilesInStaging = {};
        for (const failed of respData.failed) {
            if (failed in filesInStaging) {
                newFilesInStaging[failed] = filesInStaging[failed];
            }
        }
        alert(
            `Successfully uploaded ${Object.keys(filesInStaging).length - Object.keys(newFilesInStaging).length} image(s).
            
            ${respData.failed.length > 0 ? 'Failed to upload:' : ''}
            ${Object.keys(newFilesInStaging).join('\n')}`
        );
        filesInStaging = newFilesInStaging;
        updateFileStagingUI();
    } catch (e) {
        console.error(e);
        alert('Failed to upload images.');
    }
};
