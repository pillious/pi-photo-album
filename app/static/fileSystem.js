/*
File System Logic
*/
// {albums: {folderName: {...} | fileName: "", ...}}
const selectedFiles = { albums: {} };
// {albums: {folderName: {...}}}
const selectedFolders = { albums: {} };

let allowFileSelection = false;
let userSelectionCount = 0;

const overrideFileSystem = (fileSystem) => {
    if (fileSystem && 'albums' in fileSystem) {
        fileSystemSnapshot.albums = fileSystem.albums;
    }
};

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
                if (parent !== fsTreeRoot) {
                    // Don't allow selection of top level folders
                    selectItem.onchange = (e) => handleSelectItem(e, currPath, false);
                    folderLi.appendChild(selectItem);
                }
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
                selectItem.onchange = (e) => {
                    handleSelectItem(e, currPath, true);
                };
                fileLi.appendChild(selectItem);
                fileLi.appendChild(fileName);

                parent.appendChild(fileLi);
            }
        }
    }
};

/**
 * Creates a new folder.
 *
 * @param {Event} e
 */
const handleCreateFolder = (e) => {
    e.preventDefault();

    const fields = new FormData(e.target);
    const folderPath = securePath(fields.get('folderPath'));
    const folderName = secureFilename(fields.get('folderName').trim());

    if (folderPath === '') {
        alert('Folder path cannot be empty');
        return;
    }
    if (folderName === '') {
        alert('Folder name cannot be empty');
        return;
    }

    updateFileSystem(fileSystemSnapshot, '', folderPath + '/' + folderName);

    updateFileSystemUI();
    updateSettingsUI(settingsState);
    updateFileStagingUI();

    hideCreateFolderDialog();
};

const handleCopyFiles = async (e) => {
    e.preventDefault();

    const fields = new FormData(e.target);
    const folderPath = fields.get('folderPath');
    if (folderPath === '') {
        alert('Folder path cannot be empty');
        return;
    }

    const pathPairs = generatePathPairs(folderPath);
    console.log(pathPairs);

    if (pathPairs.length > 0) {
        const resp = await fetch('/copy-images', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ files: pathPairs }),
        });

        const data = await resp.json();
        const failedOldPaths = (data.failed || []).map((path) => path[0]);
        console.log(data);

        pathPairs
            .filter((pair) => !failedOldPaths.includes(pair.oldPath))
            .forEach((pair) =>
                updateFileSystem(fileSystemSnapshot, '', removeAlbumsPrefix(pair.newPath))
            );

        if (failedOldPaths.length > 0) {
            alert(`Failed to copy the following files:\n${failedOldPaths.join('\n')}`);
        }
        updateFileSystemUI();
    }

    toggleFileSelection();
    hideCopyFilesDialog();
};

const handleMoveFiles = async (e) => {
    e.preventDefault();

    const fields = new FormData(e.target);
    const folderPath = fields.get('folderPath');
    if (folderPath === '') {
        alert('Folder path cannot be empty');
        return;
    }

    const pathPairs = generatePathPairs(folderPath);
    console.log(pathPairs);

    if (pathPairs.length > 0) {
        const resp = await fetch('/move-images', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ files: pathPairs }),
        });

        const data = await resp.json();
        const failedOldPaths = (data.failed || []).map((path) => path[0]);

        console.log(data);

        pathPairs
            .filter((pair) => !failedOldPaths.includes(pair.oldPath))
            .forEach((pair) =>
                updateFileSystem(
                    fileSystemSnapshot,
                    removeAlbumsPrefix(pair.oldPath),
                    removeAlbumsPrefix(pair.newPath)
                )
            );

        if (failedOldPaths.length > 0)
            alert(`Failed to move the following files:\n${failedOldPaths.join('\n')}`);
        updateFileSystemUI();
    }

    toggleFileSelection();
    hideMoveFilesDialog();
};

/**
 * Deletes the selected files from the file system object and requests the server to delete them.
 */
const handleDeleteFiles = async () => {
    showLoadingSpinnerWithCaption('Deleting file(s)..');

    let filePathsToDelete = flattenObjectToPaths(selectedFiles.albums).map(
        (path) => securePath(`albums/${path}`)
    );

    // Confirmation dialog
    if (!confirm('Are you sure? This will permanently delete the selected files.')) {
        hideLoadingSpinner();
        return;
    }

    const resp = await fetch('/delete-images', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ files: filePathsToDelete }),
    });

    const data = await resp.json();
    const failed = data.failed || [];

    filePathsToDelete = filePathsToDelete.filter((path) => !failed.includes(path));
    filePathsToDelete.forEach((path) =>
        updateFileSystem(fileSystemSnapshot, removeAlbumsPrefix(path), '')
    );

    if (failed.length > 0) alert(`Failed to delete the following files:\n${failed.join('\n')}`);
    if (filePathsToDelete.length > 0) updateFileSystemUI();

    toggleFileSelection();
    hideLoadingSpinner();
};

const handleRenameFile = async (e) => {
    e.preventDefault();
    showLoadingSpinnerWithCaption('Renaming file(s)..');

    const fields = new FormData(e.target);
    const newFileName = secureFilename(fields.get('newName').trim());

    if (newFileName === '') {
        hideLoadingSpinner();
        alert('File name cannot be empty');
        return;
    }

    const selectedFilePaths = flattenObjectToPaths(selectedFiles.albums);

    console.log(selectedFolders);
    console.log(selectedFilePaths);

    let pathPairs = [];
    if (Object.keys(selectedFolders.albums).length === 0) {
        // Case: renaming a single file
        const idx = selectedFilePaths[0].lastIndexOf('/') + 1;
        const folderPath = selectedFilePaths[0].substring(0, idx);
        const fileId = selectedFilePaths[0].substring(idx + 1).split('.', 1)[0];
        const fileExt = getFileExtension(selectedFilePaths[0]);
        pathPairs.push({
            oldPath: securePath(`albums/${selectedFilePaths[0]}`),
            newPath: securePath(`albums/${folderPath}${fileId}.${newFileName}.${fileExt}`),
        });
    } else {
        // Case: renaming a folder
        let loc = selectedFolders.albums;
        const folderPath = [];
        while (Object.keys(loc).length > 0) {
            const [key, val] = Object.entries(loc)[0];
            folderPath.push(key);
            loc = val;
        }
        const oldFolderPrefix = folderPath.join('/');
        folderPath[folderPath.length - 1] = newFileName;
        const newFolderPrefix = folderPath.join('/');
        pathPairs = selectedFilePaths.map((path) => {
            if (path.startsWith(oldFolderPrefix))
                return {
                    oldPath: securePath(`albums/${path}`),
                    newPath: securePath(`albums/${newFolderPrefix + path.slice(oldFolderPrefix.length)}`),
                };
        });
    }

    console.log(pathPairs);

    if (pathPairs.length > 0) {
        const resp = await fetch('/move-images', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ files: pathPairs }),
        });

        const data = await resp.json();
        const failedOldPaths = (data.failed || []).map((path) => path[0]);

        console.log(data);

        // TODO: if the renamed item is a folder, don't need to rename each file individually, just move the folder obj.
        pathPairs
            .filter((pair) => !failedOldPaths.includes(pair.oldPath))
            .forEach((pair) =>
                updateFileSystem(
                    fileSystemSnapshot,
                    removeAlbumsPrefix(pair.oldPath),
                    removeAlbumsPrefix(pair.newPath)
                )
            );

        if (failedOldPaths.length > 0)
            alert(`Failed to move the following files:\n${failedOldPaths.join('\n')}`);
        updateFileSystemUI();
    }

    toggleFileSelection();
    hideRenameFileDialog();
    hideLoadingSpinner();
};

/**
 * Generates path pairs for moving/copying files based on selected files and folders.
 *
 * @param {String} folderPath - Target folder path.
 * @returns {Array} Array of path pairs {oldPath: string, newPath: string}.
 */
const generatePathPairs = (folderPath) => {
    const selectedFilePaths = flattenObjectToPaths(selectedFiles.albums);
    const prefixReplace = {}; // folder path prefixes to replace {oldPrefix: newPrefix}

    // Generates the folder path prefixes to replace
    const path = [];
    const loc = [selectedFolders.albums];
    while (loc.length > 0) {
        const currLoc = loc.pop();
        for (const [key, val] of Object.entries(currLoc)) {
            if (Object.entries(val).length === 0) {
                path.push(key);
                prefixReplace[path.join('/')] = `${folderPath}/${key}`;
            } else {
                path.push(key);
                loc.push(val);
            }
        }
    }
    console.log(selectedFilePaths);
    console.log(prefixReplace);

    // Creates the path pairs: {oldPath: str, newPath: str}[]
    const pathPairs = selectedFilePaths.map((path) => {
        for (const [key, val] of Object.entries(prefixReplace)) {
            if (path.startsWith(key)) {
                return {
                    oldPath: securePath(`albums/${path}`),
                    newPath: securePath(`albums/${val}${path.substring(key.length)}`),
                };
            }
        }
        const fileName = path.substring(path.lastIndexOf('/') + 1);
        return {
            oldPath: securePath(`albums/${path}`),
            newPath: securePath(`albums/${folderPath}/${fileName}`),
        };
    });

    return pathPairs;
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
        let loc = [fileSystem.albums];
        for (const part of currFilePathParts) {
            loc.push(loc[loc.length - 1][part]);
        }
        delete loc[loc.length - 1][currFileName];

        // Delete empty folders
        for (let i = loc.length - 2; i >= 0; i--) {
            const part = currFilePathParts[i];
            if (Object.keys(loc[i + 1]).length === 0) {
                delete loc[i][part];
            } else {
                break;
            }
        }
    } else {
        // Move
        updateFileSystem(fileSystem, '', newFilePath);
        updateFileSystem(fileSystem, currFilePath, '');
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
    if (isFile) {
        if (e.target.checked) updateFileSystem(selectedFiles, '', path);
        else updateFileSystem(selectedFiles, path, '');
    } else {
        // TODO: can this be cleanup up a bit?
        const parts = path.split('/');

        let locFiles = [selectedFiles.albums];
        let locFolders = [selectedFolders.albums];
        let snapshotLoc = fileSystemSnapshot.albums;
        for (let i = 0; i < parts.length - 1; i++) {
            const part = parts[i];
            if (!(part in locFiles[i])) locFiles[i][part] = {};
            if (!(part in locFolders[i])) locFolders[i][part] = {};
            locFiles.push(locFiles[i][part]);
            locFolders.push(locFolders[i][part]);
            snapshotLoc = snapshotLoc[part];
        }

        if (e.target.checked) {
            locFiles[locFiles.length - 1][parts[parts.length - 1]] = structuredClone(
                snapshotLoc[parts[parts.length - 1]]
            );
            locFolders[locFolders.length - 1][parts[parts.length - 1]] = {};
        } else {
            delete locFiles[locFiles.length - 1][parts[parts.length - 1]];
            delete locFolders[locFolders.length - 1][parts[parts.length - 1]];

            // Delete empty folders
            for (let i = locFiles.length - 2; i >= 0; i--) {
                const part = parts[i];
                if (Object.keys(locFiles[i + 1]).length === 0) {
                    delete locFiles[i][part];
                } else {
                    break;
                }
            }
            for (let i = locFolders.length - 2; i >= 0; i--) {
                const part = parts[i];
                if (Object.keys(locFolders[i + 1]).length === 0) {
                    delete locFolders[i][part];
                } else {
                    break;
                }
            }
        }

        // Propagate change to children checkboxes
        const children = document.querySelectorAll(`[data-album-path^="${path}/"]`);
        for (const child of children) {
            const checkbox = child.querySelector('input[type="checkbox"]');
            if (checkbox) {
                if (checkbox.checked && !checkbox.disabled) setToolStates(-1);
                checkbox.checked = e.target.checked;
                checkbox.disabled = e.target.checked;
            }
        }
    }

    setToolStates(e.target.checked ? 1 : -1);
};

/**
 * Toggles the file selection mode.
 * When toggled off, the selected files are cleared.
 */
const toggleFileSelection = () => {
    allowFileSelection = !allowFileSelection;
    if (allowFileSelection) {
        setToolStates(0);
    } else {
        selectedFiles.albums = {};
        selectedFolders.albums = {};
        setToolStates(-userSelectionCount);
    }
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
 * Handles the enabled/disabled state of the file system tools based on the user selection count.
 *
 * @param {number} change Update the user selection count by this amount.
 */
const setToolStates = (change) => {
    userSelectionCount += change;
    document.getElementById('file-system-tools-rename').disabled = userSelectionCount !== 1;
    document.getElementById('file-system-tools-copy').disabled = userSelectionCount < 1;
    document.getElementById('file-system-tools-move').disabled = userSelectionCount < 1;
    document.getElementById('file-system-tools-delete').disabled = userSelectionCount < 1;
};

/**
 * Handles events sent from the server and updates the file system object.
 *
 * @param {string} data The data sent from the server as stringified JSON.
 */
const handleEvent = (data) => {
    const event = JSON.parse(data);
    console.log(event);

    for (const message of event.events) {
        switch (message.event) {
            case 'PUT': {
                const path = removeAlbumsPrefix(message.path);
                console.log('PUT event: ' + path);
                updateFileSystem(fileSystemSnapshot, '', path);
                break;
            }
            case 'DELETE': {
                const path = removeAlbumsPrefix(message.path);
                console.log('DELETE event: ' + path);
                updateFileSystem(fileSystemSnapshot, path, '');
                break;
            }
            case 'MOVE': {
                const oldPath = removeAlbumsPrefix(message.path);
                const newPath = removeAlbumsPrefix(message.newPath);
                console.log('MOVE event: ' + oldPath + ' -> ' + newPath);
                updateFileSystem(fileSystemSnapshot, oldPath, newPath);
                break;
            }
            case 'RESYNC': {
                if ('fileStructure' in message) overrideFileSystem(message.fileStructure);
                console.log('RESYNC event:');
                console.log(message.fileStructure);
                refreshUI();
                break;
            }
            case 'LOADING': {
                const loading = message.loading || false;
                console.log('LOADING event: ' + loading + ' - ' + message.message);
                if (loading) {
                    showLoadingSpinnerWithCaption(message.message || '');
                } else {
                    hideLoadingSpinner();
                }
                break;
            }
            default: {
                console.warn('UNKNOWN event: ' + message.event);
                break;
            }
        }
    }

    if (event.events.length > 0) {
        updateFileSystemUI();
    }
};
