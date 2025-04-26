/*
File System Logic
*/
// {albums: {folderName: {...} | fileName: "", ...}}
const selectedFiles = { albums: {} };
let allowFileSelection = false;

/**
 * Creates the file system UI based on the file system object.
 */
const updateFileSystemUI = () => {
    const fsTreeRoot = document.querySelector('[data-fs-tree-]');
    fsTreeRoot.innerHTML = '';

    const stack = [];
    stack.push([fileSystemSnapshot.albums, fsTreeRoot, '']);

    while (stack.length > 0) {
        const [fsObj, parentElem, elemId] = stack.pop();
        const parent = parentElem.querySelector(`[data-fs-tree-${elemId}]`) || fsTreeRoot;
        const parentPath = parent.getAttribute('data-album-path') || '';
        for (const [key, val] of Object.entries(fsObj)) {
            const currPath = parentPath === '' ? key : `${parentPath}/${key}`;

            // Checkbox for file selection
            const selectItem = document.createElement('input');
            selectItem.type = 'checkbox';
            selectItem.hidden = !allowFileSelection;

            if (typeof val === 'object') {
                // Folder Name List Item
                const folderLi = document.createElement('li');
                folderLi.classList.add('album-name');
                folderLi.setAttribute('data-album-path', currPath);
                const folderName = document.createElement('span');
                folderName.innerHTML = key;
                selectItem.onchange = (e) => handleSelectItem(e, currPath, false);
                folderLi.appendChild(selectItem);
                folderLi.appendChild(folderName);
                parent.appendChild(folderLi);

                // Folder Sublist
                const folderUl = document.createElement('ul');
                folderUl.setAttribute(`data-fs-tree-${key}`, '');
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

                stack.push([val, parent, key]);
            } else {
                const fileLi = document.createElement('li');
                fileLi.setAttribute('data-album-path', currPath);
                fileName = document.createElement('span');
                fileName.innerHTML = key.substring(key.indexOf('.') + 1);
                selectItem.onchange = (e) => handleSelectItem(e, currPath, true);
                fileLi.appendChild(selectItem);
                fileLi.appendChild(fileName);

                parent.appendChild(fileLi);
            }
        }
    }
};

/**
 * Shows the create folder dialog.
 * The dialog is populated with the available album paths.
 */
const showCreateFolderDialog = () => {
    document.getElementById('create-folder-dialog').showModal();
    document.querySelector('.overlay').style.display = 'block';

    const albumPaths = getAlbumPaths(fileSystemSnapshot, false).map(
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

/**
 * Hides the create folder dialog and resets the form.
 */
const hideCreateFolderDialog = () => {
    document.getElementById('create-folder-dialog').close();
    document.querySelector('.overlay').style.display = 'none';

    const form = document.getElementById('create-folder-dialog').querySelector('form');
    form.reset();
};

/**
 * Creates a new folder.
 * 
 * @param {Event} e 
 */
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

    updateFileSystem(fileSystemSnapshot, '', folderPath + folderName);

    updateFileSystemUI();
    updateSettingsUI(settingsState);
    updateFileStagingUI();

    hideCreateFolderDialog();
};

/**
 * Updates the file system object based on the following rules:
 *
 * - If currFilePath is empty and newFilePath is nonempty, creates a new file (and creates any missing intermediate folders). Does nothing if the file already exists.
 * - If currFilePath is nonempty and newFilePath is empty, deletes the file.
 * - If currFilePath and newFilePath are nonempty, moves the file.
 * @param {Object<string, string | Object>} fileSystem
 * @param {String} currFilePath
 * @param {String} newFilePath
 */
const updateFileSystem = (fileSystem, currFilePath, newFilePath) => {
    if (currFilePath === newFilePath) {
        return;
    }

    if (currFilePath === '' && newFilePath !== '') {
        // Create
        let isFolder = !isImageFile(newFilePath);
        const newFilePathParts = newFilePath.split('/');
        let loc = fileSystem.albums;
        for (let i = 0; i < newFilePathParts.length - 1; i++) {
            const part = newFilePathParts[i];
            if (!(part in loc)) {
                loc[part] = {};
            }
            loc = loc[part];
        }
        if (!(newFilePathParts[newFilePathParts.length - 1] in loc)) {
            loc[newFilePathParts[newFilePathParts.length - 1]] = isFolder ? {} : '';
        }
    } else if (currFilePath !== '' && newFilePath === '') {
        // Delete
        const currFilePathParts = currFilePath.split('/');
        const currFileName = currFilePathParts.pop();
        let loc = fileSystem.albums;
        for (const part of currFilePathParts) {
            loc = loc[part];
        }
        delete loc[currFileName];
    } else {
        // Move
        const currFilePathParts = currFilePath.split('/');
        const newFilePathParts = newFilePath.split('/');
        const currFileName = currFilePathParts.pop();
        let loc = fileSystem.albums;
        for (const part of currFilePathParts) {
            loc = loc[part];
        }
        loc[newFilePathParts[newFilePathParts.length - 1]] = loc[currFileName];
        delete loc[currFileName];
    }
};

/**
 * Updates the selected files object. If the item selected/unselected is a folder, the change is propagated to all its children.
 *
 * @param {Event} e on change event
 * @param {String} path the path of the selected file or folder
 * @param {Boolean} isFile
 */
const handleSelectItem = (e, path, isFile) => {
    console.log(path, isFile);

    if (isFile) {
        if (e.target.checked) updateFileSystem(selectedFiles, '', path);
        else updateFileSystem(selectedFiles, path, '');
    } else {
        const parts = path.split('/');

        const folders = [];

        let loc = selectedFiles.albums;
        let snapshotLoc = fileSystemSnapshot.albums;
        for (let i = 0; i < parts.length - 1; i++) {
            const part = parts[i];
            if (!(part in loc)) {
                loc[part] = {};
            }
            loc = loc[part];
            snapshotLoc = snapshotLoc[part];
            folders;
            console.log(loc, snapshotLoc);
        }

        if (e.target.checked) {
            loc[parts[parts.length - 1]] = structuredClone(snapshotLoc[parts[parts.length - 1]]);
        } else {
            delete loc[parts[parts.length - 1]];
        }

        // Propagate change to children checkboxes
        const children = document.querySelectorAll(`[data-album-path^="${path}/"]`);
        for (const child of children) {
            const checkbox = child.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = e.target.checked;
                checkbox.disabled = e.target.checked;
            }
        }
    }

    console.log(selectedFiles);
};

/**
 * Toggles the file selection mode. When toggled off, the selected files are cleared.
 */
const toggleFileSelection = () => {
    allowFileSelection = !allowFileSelection;
    if (!allowFileSelection) selectedFiles.albums = {};
    const selectItems = document
        .querySelector('[data-fs-tree-]')
        .querySelectorAll('input[type="checkbox"]');
    for (const item of selectItems) {
        item.hidden = !allowFileSelection;
        if (!allowFileSelection) {
            item.checked = false;
            item.disabled = false;
        }
    }
    const fileSelectionTools = document.querySelectorAll('.file-system-tools');
    for (const elem of fileSelectionTools) {
        elem.style.display = allowFileSelection ? 'inline' : 'none';
    }
};

/**
 * Handles events sent from the server and updates the file system object.
 *
 * @param {string} data The data sent from the server as stringified JSON.
 */
const handleEvent = (data) => {
    const event = JSON.parse(data);
    console.log(event);

    for (const e of event.events) {
        const message = JSON.parse(e);
        switch (message.event) {
            case 'PUT':
                // remove the leading 'albums/' from the path
                messagePath = message.path.substring(message.path.indexOf('/') + 1);
                updateFileSystem(fileSystemSnapshot, '', messagePath);
                console.log('PUT event: ' + messagePath);
                break;
            case 'DELETE':
                messagePath = message.path.substring(message.path.indexOf('/') + 1);
                updateFileSystem(fileSystemSnapshot, messagePath, '');
                console.log('DELETE event: ' + messagePath);
                break;
            case 'MOVE':
                break;
            default:
                console.log('Unknown event type: ' + message.event);
                break;
        }
    }

    if (event.events.length > 0) {
        updateFileSystemUI();
    }
};

/**
 * Deletes the selected files from the file system object and requests the server to delete them.
 */
const deleteFiles = async () => {
    let filePathsToDelete = flattenObjectToPaths(selectedFiles.albums).map(
        (path) => `albums/${path}`
    );
    console.log(filePathsToDelete);

    const resp = await fetch('/delete-images', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ files: filePathsToDelete }),
    });

    const data = await resp.json();
    const failed = data.failed || [];

    filePathsToDelete = filePathsToDelete
        .filter((path) => !failed.includes(path))
        .map((path) => path.substring(path.indexOf('/') + 1));
    filePathsToDelete.forEach((path) => updateFileSystem(fileSystemSnapshot, path, ''));
    if (filePathsToDelete.length > 0) updateFileSystemUI();
    toggleFileSelection();
};
