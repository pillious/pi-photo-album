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

                // Button to create a subfolder
                const createAlbumBtn = document.createElement('button');
                createAlbumBtn.innerHTML = 'Create Album';
                createAlbumBtn.classList.add('create-album-btn');
                createAlbumBtn.onclick = () => {
                    const albumName = prompt('Enter album name');
                    if (albumName !== null && albumName.trim() !== '' && !(albumName in val)) {
                        console.log((currPath + '/' + albumName.trim()).substring(1));
                        updateFileSystem('', (currPath + '/' + albumName.trim()).substring(1));
                        updateFileSystemUI();
                        updateSettingsUI(settingsState);
                    }
                };

                folderLi.appendChild(hideBtn);
                folderLi.appendChild(createAlbumBtn);

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

// Update the file system object with the new file path
// If currFilePath is empty and newFilePath is nonempty, creates a new file.
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
        for (let i = 0; i < newFilePathParts.length; i++) {
            if (i === newFilePathParts.length - 1) {
                loc[newFilePathParts[i]] = isFolder ? {} : '';
            } else {
                loc = loc[newFilePathParts[i]];
            }
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
