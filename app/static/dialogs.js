/**
 * Shows the create folder dialog.
 * The dialog is populated with the available album paths.
 */
const showCreateFolderDialog = () => {
    document.getElementById('create-folder-dialog').showModal();
    showOverlay();

    const albumPaths = removeAlbumsPrefixes(getAlbumPaths(fileSystemSnapshot, false))

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
    hideOverlay();

    const form = document.getElementById('create-folder-dialog').querySelector('form');
    form.reset();
};

/**
 * Shows the move files dialog.
 * The dialog is populated with the available album paths.
 */
const showMoveFilesDialog = () => {
    document.getElementById('move-files-dialog').showModal();
    showOverlay();
    
    const albumPaths = removeAlbumsPrefixes(getAlbumPaths(fileSystemSnapshot, false))

    const select = document.getElementById('move-files-dialog').querySelector('select');
    select.innerHTML = select.firstElementChild.outerHTML;
    for (const path of albumPaths) {
        const option = document.createElement('option');
        option.value = path;
        option.innerHTML = path;
        select.appendChild(option);
    }
}

/**
 * Hides the move files dialog and resets the form.
 */
const hideMoveFilesDialog = () => {
    document.getElementById('move-files-dialog').close();
    hideOverlay();

    const form = document.getElementById('move-files-dialog').querySelector('form');
    form.reset();
}

/**
 * Shows the rename file dialog.
 */
const showRenameFileDialog = () => {
    document.getElementById('rename-file-dialog').showModal();
    showOverlay();

    const form = document.getElementById('rename-file-dialog').querySelector('form');
    form.reset();
}

/**
 * Hides the rename file dialog and resets the form.
 */
const hideRenameFileDialog = () => {
    document.getElementById('rename-file-dialog').close();
    hideOverlay();

    const form = document.getElementById('rename-file-dialog').querySelector('form');
    form.reset();
}

const showOverlay = () => {
    document.querySelector('.overlay').style.display = 'block';
}

const hideOverlay = () => {
    document.querySelector('.overlay').style.display = 'none';
}