/*
File System Logic
*/
const updateFileSystemUI = () => {
    const fileSystemTreeRoot = document.getElementById('file-system-tree');
    fileSystemTreeRoot.innerHTML = '';

    const stack = [];
    stack.push([fileStructureSnapshot.albums, 'file-system-tree']);

    while (stack.length > 0) {
        const [fsObj, elemId] = stack.pop();
        const parent = document.getElementById(elemId);
        const parentPath = parent.getAttribute('data-album-path') || '';
        for (const [key, val] of Object.entries(fsObj)) {
            const currPath = parentPath + '/' + key;
            if (typeof val === 'object') {
                // Folder Name List Item
                const folderLi = document.createElement('li');
                folderLi.classList.add('album-name');
                folderLi.innerHTML = key;
                folderLi.setAttribute('data-album-path', currPath);
                parent.appendChild(folderLi);

                // Folder Sublist
                const folderUl = document.createElement('ul');
                folderUl.id = key;
                folderUl.setAttribute('data-album-path', currPath);
                folderUl.style.display = 'none'; // Defaults to hiding files
                parent.appendChild(folderUl);

                // Button to hide files in folder
                const hideBtn = document.createElement('button');
                hideBtn.innerHTML = 'Show';
                hideBtn.classList.add('hide-album-btn');
                hideBtn.onclick = () => {
                    folderUl.style.display = folderUl.style.display === 'none' ? 'block' : 'none';
                    hideBtn.innerHTML = folderUl.style.display === 'none' ? 'Show' : 'Hide';
                };

                folderLi.appendChild(hideBtn);

                stack.push([val, key]);
            } else {
                const fileLi = document.createElement('li');
                fileLi.innerHTML = key;
                fileLi.setAttribute('data-album-path', currPath);
                parent.appendChild(fileLi);
            }
        }
    }
};

const showCreateFolderDialog = () => {
    document.getElementById('create-folder-dialog').showModal();
    document.querySelector('.overlay').style.display = 'block';

    const albumPaths = getAlbumPaths(fileStructureSnapshot, false).map(
        // Remove the leading 'albums/' and add a trailing '/'
        (path) => path.substring(path.indexOf('/') + 1) + '/'
    );

    const select = document.getElementById('create-folder-dialog').querySelector('select');
    select.innerHTML = select.firstElementChild.outerHTML;
    for (const path of albumPaths) {
        const option = document.createElement('option');
        option.value = path;
        option.innerHTML = path;
        select.appendChild(option);
    }
};

const hideCreateFolderDialog = () => {
    document.getElementById('create-folder-dialog').close();
    document.querySelector('.overlay').style.display = 'none';

    const form = document.getElementById('create-folder-dialog').querySelector('form');
    form.reset();
}

const handleCreateFolder = (e) => {
    e.preventDefault();

    const fields = new FormData(e.target);
    const folderPath = fields.get('folderPath');
    const folderName = secureFilename(fields.get('folderName').trim());

    if (folderPath === '') {
        alert('Folder path cannot be empty');
        return;
    }
    if (folderName === '') {
        alert('Folder name cannot be empty');
        return;
    }

    updateFileSystem('', folderPath + folderName);

    updateFileSystemUI();
    updateSettingsUI(settingsState);
    updateFileStagingUI();

    hideCreateFolderDialog();
};

// Update the file system object with the new file path
// If currFilePath is empty and newFilePath is nonempty, creates a new file. Does nothing if the file already exists.
// If currFilePath is nonempty and newFilePath is empty, deletes the file.
// If currFilePath and newFilePath are nonempty, moves the file.
const updateFileSystem = (currFilePath, newFilePath) => {
    if (currFilePath === newFilePath) {
        return;
    }

    if (currFilePath === '' && newFilePath !== '') {
        // Create
        let isFolder = !isImageFile(newFilePath);
        const newFilePathParts = newFilePath.split('/');
        let loc = fileStructureSnapshot.albums;
        for (let i = 0; i < newFilePathParts.length - 1; i++) {
            loc = loc[newFilePathParts[i]];
        }
        if (!(newFilePathParts[newFilePathParts.length - 1] in loc)) {
            loc[newFilePathParts[newFilePathParts.length - 1]] = isFolder ? {} : '';
        }
    } else if (currFilePath !== '' && newFilePath === '') {
        // Delete
        const currFilePathParts = currFilePath.split('/');
        const currFileName = currFilePathParts.pop();
        let loc = fileStructureSnapshot.albums;
        for (const part of currFilePathParts) {
            loc = loc[part];
        }
        delete loc[currFileName];
    } else {
        // Move
        const currFilePathParts = currFilePath.split('/');
        const newFilePathParts = newFilePath.split('/');
        const currFileName = currFilePathParts.pop();
        let loc = fileStructureSnapshot.albums;
        for (const part of currFilePathParts) {
            loc = loc[part];
        }
        loc[newFilePathParts[newFilePathParts.length - 1]] = loc[currFileName];
        delete loc[currFileName];
    }
};
